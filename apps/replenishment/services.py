from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.facilities.models import Facility
from apps.medicines.models import Medicine

from apps.replenishment.models import (
    ReplenishmentRequest,
    ReplenishmentRequestLine,
    ReplenishmentApproval,
)

from apps.inventory.stock_policy_services import (
    evaluate_stock_policy,
)


def validate_facility(facility_id, organization_id=None):
    facility = (
        Facility.objects.filter(
            pk=facility_id,
            is_active=True,
        )
        .select_related("organization")
        .first()
    )

    if not facility:
        raise ValidationError("Active facility not found.")

    if organization_id and facility.organization_id != organization_id:
        raise ValidationError("Facility does not belong to the selected organization.")

    return facility


def create_replenishment_request(
    *,
    facility_id,
    requested_by,
    justification,
    items,
    priority="NORMAL",
    source="MANUAL",
    notes="",
):
    """
    Create a draft request with one or more medicine lines.

    Does not reserve or modify inventory.
    """
    if not justification or not justification.strip():
        raise ValidationError("A justification is required.")

    if not items:
        raise ValidationError("At least one medicine is required.")

    if priority not in ReplenishmentRequest.Priority.values:
        raise ValidationError("Invalid request priority.")

    if source not in ReplenishmentRequest.Source.values:
        raise ValidationError("Invalid request source.")

    facility = validate_facility(facility_id)

    seen_medicines = set()

    with transaction.atomic():
        request = ReplenishmentRequest.objects.create(
            facility=facility,
            organization=facility.organization,
            requested_by=requested_by,
            priority=priority,
            source=source,
            justification=justification.strip(),
            notes=notes,
            status=ReplenishmentRequest.Status.DRAFT,
        )

        for item in items:
            medicine_id = item["medicine_id"]

            if str(medicine_id) in seen_medicines:
                raise ValidationError("A medicine can appear only once in a request.")

            seen_medicines.add(str(medicine_id))

            medicine = Medicine.objects.filter(pk=medicine_id).first()

            if not medicine:
                raise ValidationError(f"Medicine {medicine_id} does not exist.")

            quantity = Decimal(str(item["requested_quantity"]))

            if quantity <= 0:
                raise ValidationError("Requested quantity must be positive.")

            recommended_quantity = Decimal(str(item.get("recommended_quantity", "0")))

            if recommended_quantity < 0:
                raise ValidationError("Recommended quantity cannot be negative.")

            ReplenishmentRequestLine.objects.create(
                request=request,
                medicine=medicine,
                requested_quantity=quantity,
                recommended_quantity=recommended_quantity,
                unit_code=item["unit_code"].strip().upper(),
                preferred_supplier_id=item.get("preferred_supplier_id"),
                reason=item.get("reason", ""),
            )

    return request


@transaction.atomic
def generate_policy_replenishment_request(
    *,
    facility_id,
    medicine_ids,
    requested_by,
    justification,
    priority="NORMAL",
):
    """
    Create a draft request from Phase 20 policy evaluations.

    Only medicines with a configured active policy and a positive
    recommended quantity are included.
    """
    if not medicine_ids:
        raise ValidationError("Select at least one medicine.")

    items = []

    for medicine_id in medicine_ids:
        result = evaluate_stock_policy(
            facility_id=facility_id,
            medicine_id=medicine_id,
        )

        if not result.get("policy_configured"):
            raise ValidationError(f"No active stock policy for medicine {medicine_id}.")

        quantity = Decimal(result["recommended_quantity"])

        if quantity <= 0:
            continue

        medicine = Medicine.objects.get(pk=medicine_id)

        # Unit codes should be standardized with the medicine's
        # measurement unit in your Phase 11 model.
        unit_code = (
            getattr(
                medicine,
                "unit_code",
                None,
            )
            or "UNIT"
        )

        items.append(
            {
                "medicine_id": medicine.pk,
                "requested_quantity": quantity,
                "recommended_quantity": quantity,
                "unit_code": unit_code,
                "reason": (
                    f"Generated from stock policy. "
                    f"Policy status: {result['status']}; "
                    f"reorder point: {result['reorder_point']}."
                ),
            }
        )

    if not items:
        raise ValidationError("No positive replenishment recommendations were found.")

    return create_replenishment_request(
        facility_id=facility_id,
        requested_by=requested_by,
        justification=justification,
        items=items,
        priority=priority,
        source=ReplenishmentRequest.Source.POLICY,
    )


@transaction.atomic
def submit_replenishment_request(request_id, user):
    from apps.replenishment.approval_services import (
        initialize_approval_workflow,
    )

    request = ReplenishmentRequest.objects.select_for_update().get(pk=request_id)

    if request.status not in [
        ReplenishmentRequest.Status.DRAFT,
        ReplenishmentRequest.Status.REVISION_REQUESTED,
    ]:
        raise ValidationError(
            "Only draft or revision-requested requests can be submitted."
        )

    if request.requested_by_id != user.pk:
        raise ValidationError("Only the requester can submit this request.")

    if not request.items.exists():
        raise ValidationError("A request must contain at least one medicine.")

    # Remove old unfinished stages when a revised request is resubmitted.
    if request.status == ReplenishmentRequest.Status.REVISION_REQUESTED:
        if request.approval_stages.filter(
            status=ReplenishmentApproval.Status.PENDING
        ).exists():
            raise ValidationError(
                "Cannot resubmit while approval stages remain pending."
            )

        # Preserve completed approval history. A production workflow
        # should create a new approval cycle rather than delete history.
        raise ValidationError(
            "Revision resubmission requires a new approval cycle. "
            "This will be implemented in Section 22.10."
        )

    request.status = ReplenishmentRequest.Status.SUBMITTED
    request.submitted_at = timezone.now()

    request.save(
        update_fields=[
            "status",
            "submitted_at",
            "updated_at",
        ]
    )

    initialize_approval_workflow(request)

    return request


@transaction.atomic
def approve_replenishment_request(
    request_id,
    user,
    approved_quantities=None,
):
    request = ReplenishmentRequest.objects.select_for_update().get(pk=request_id)

    if request.status != ReplenishmentRequest.Status.SUBMITTED:
        raise ValidationError("Only submitted requests can be approved.")

    if request.requested_by_id == user.pk:
        raise ValidationError("The requester cannot approve their own request.")

    approved_quantities = approved_quantities or {}

    lines = list(request.items.select_for_update().all())

    for line in lines:
        value = approved_quantities.get(
            str(line.pk),
            line.requested_quantity,
        )

        quantity = Decimal(str(value))

        if quantity < 0:
            raise ValidationError("Approved quantities cannot be negative.")

        line.approved_quantity = quantity
        line.save(
            update_fields=[
                "approved_quantity",
                "updated_at",
            ]
        )

    if not any(line.approved_quantity > 0 for line in lines):
        raise ValidationError(
            "At least one medicine must have a positive approved quantity."
        )

    request.status = ReplenishmentRequest.Status.APPROVED
    request.approved_by = user
    request.approved_at = timezone.now()

    request.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    return request


@transaction.atomic
def reject_replenishment_request(
    request_id,
    user,
    reason,
):
    request = ReplenishmentRequest.objects.select_for_update().get(pk=request_id)

    if request.status != ReplenishmentRequest.Status.SUBMITTED:
        raise ValidationError("Only submitted requests can be rejected.")

    if request.requested_by_id == user.pk:
        raise ValidationError("The requester cannot reject their own request.")

    if not reason or not reason.strip():
        raise ValidationError("A rejection reason is required.")

    request.status = ReplenishmentRequest.Status.REJECTED
    request.rejected_by = user
    request.rejected_at = timezone.now()
    request.rejection_reason = reason.strip()

    request.save(
        update_fields=[
            "status",
            "rejected_by",
            "rejected_at",
            "rejection_reason",
            "updated_at",
        ]
    )

    return request


@transaction.atomic
def cancel_replenishment_request(
    request_id,
    user,
    reason="",
):
    request = ReplenishmentRequest.objects.select_for_update().get(pk=request_id)

    if request.status not in [
        ReplenishmentRequest.Status.DRAFT,
        ReplenishmentRequest.Status.SUBMITTED,
    ]:
        raise ValidationError("Only draft or submitted requests can be cancelled.")

    if request.requested_by_id != user.pk and not user.is_superuser:
        raise ValidationError(
            "Only the requester or an authorized administrator "
            "can cancel this request."
        )

    request.status = ReplenishmentRequest.Status.CANCELLED
    request.cancelled_by = user
    request.cancelled_at = timezone.now()

    if reason:
        request.notes = f"{request.notes}\nCancellation: {reason}".strip()

    request.save(
        update_fields=[
            "status",
            "cancelled_by",
            "cancelled_at",
            "notes",
            "updated_at",
        ]
    )

    return request
