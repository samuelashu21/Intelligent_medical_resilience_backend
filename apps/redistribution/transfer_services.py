from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.facilities.models import Facility
from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
)

from apps.redistribution.optimization_models import (
    RedistributionOptimizationAllocation,
)

from apps.redistribution.transfer_models import (
    TransferRequest,
    TransferRequestLine,
    TransferApprovalStage,
    TransferApprovalDecision,
    TransferStatus,
    TransferSource,
    TransferPriority,
    TransferApprovalDecisionType,
)


ZERO = Decimal("0")


def record_transfer_audit(
    *,
    user,
    action,
    transfer,
    description,
    changes=None,
    metadata=None,
):
    """
    Adapt this wrapper to the exact Phase 10 audit service
    signature in your project.
    """

    from apps.audit.services import record_audit_event

    record_audit_event(
        actor=user,
        category="SYSTEM",
        action=action,
        target_type="TransferRequest",
        target_id=str(transfer.pk),
        description=description,
        organization=transfer.organization,
        changes=changes or {},
        metadata=metadata or {},
    )


def get_transfer_organization(
    donor_facility,
    recipient_facility,
):
    """
    Require both facilities to belong to the same
    organization for this initial transfer workflow.

    Cross-region/national transfers need an explicit
    governing organization policy and will be added
    through the approval configuration.
    """

    if (
        donor_facility.organization_id
        != recipient_facility.organization_id
    ):
        raise ValidationError(
            "Cross-organization transfers require an authorized "
            "shared governing organization policy."
        )

    return donor_facility.organization


def validate_transfer_batch(
    *,
    donor_facility,
    medicine,
    batch,
    quantity,
):
    if batch.medicine_id != medicine.pk:
        raise ValidationError(
            "The batch does not belong to the requested medicine."
        )

    if batch.warehouse.facility_id != donor_facility.pk:
        raise ValidationError(
            "The selected batch does not belong to the donor facility."
        )

    if not batch.warehouse.is_active:
        raise ValidationError(
            "The donor warehouse is inactive."
        )

    if not donor_facility.is_active:
        raise ValidationError(
            "The donor facility is inactive."
        )

    if batch.expiry_date < timezone.localdate():
        raise ValidationError(
            "Expired batches cannot be transferred."
        )

    if quantity <= ZERO:
        raise ValidationError(
            "Transfer quantity must be positive."
        )


@transaction.atomic
def create_transfer_from_optimization(
    *,
    optimization_run_id,
    user,
    justification,
    priority=TransferPriority.NORMAL,
):
    """
    Create one transfer request per donor-recipient pair
    from the accepted allocations in a completed optimization run.

    Does not reserve or deduct inventory.
    """

    from apps.redistribution.optimization_models import (
        RedistributionOptimizationRun,
    )

    run = (
        RedistributionOptimizationRun.objects
        .select_for_update()
        .get(pk=optimization_run_id)
    )

    if run.status != "COMPLETED":
        raise ValidationError(
            "Only completed optimization runs can create transfers."
        )

    allocations = list(
        RedistributionOptimizationAllocation.objects
        .select_for_update()
        .filter(
            optimization_run=run,
            status="PROPOSED",
        )
        .select_related(
            "medicine",
            "batch",
            "batch__warehouse",
            "donor_facility",
            "recipient_facility",
        )
        .order_by(
            "donor_facility_id",
            "recipient_facility_id",
            "medicine_id",
        )
    )

    if not allocations:
        raise ValidationError(
            "There are no unused proposed allocations in this run."
        )

    # Verify that every allocation is within the user's
    # authorized donor and recipient scope.
    from apps.accounts.scope_services import (
        get_user_accessible_facility_ids,
    )

    if user.is_superuser:
        allowed_facility_ids = set(
            Facility.objects.filter(
                is_active=True
            ).values_list("id", flat=True)
        )
    else:
        allowed_facility_ids = set(
            get_user_accessible_facility_ids(
                user,
                permission_code="redistribution.transfer.create",
            )
        )

    grouped = {}

    for allocation in allocations:

        if (
            allocation.donor_facility_id
            not in allowed_facility_ids
            or allocation.recipient_facility_id
            not in allowed_facility_ids
        ):
            raise ValidationError(
                "You are not authorized to create transfers "
                "for every facility in this optimization run."
            )

        key = (
            allocation.donor_facility_id,
            allocation.recipient_facility_id,
        )

        grouped.setdefault(key, []).append(allocation)

    created_requests = []

    for (donor_id, recipient_id), items in grouped.items():

        donor = Facility.objects.get(pk=donor_id)
        recipient = Facility.objects.get(pk=recipient_id)

        organization = get_transfer_organization(
            donor,
            recipient,
        )

        transfer = TransferRequest.objects.create(
            source=TransferSource.OPTIMIZATION,
            optimization_run=run,
            donor_facility=donor,
            recipient_facility=recipient,
            organization=organization,
            requested_by=user,
            priority=priority,
            status=TransferStatus.DRAFT,
            justification=justification,
        )

        for allocation in items:

            batch = (
                StockBatch.objects
                .select_related(
                    "warehouse",
                    "warehouse__facility",
                )
                .get(pk=allocation.batch_id)
            )

            quantity = Decimal(str(allocation.quantity))

            validate_transfer_batch(
                donor_facility=donor,
                medicine=allocation.medicine,
                batch=batch,
                quantity=quantity,
            )

            TransferRequestLine.objects.create(
                transfer=transfer,
                optimization_allocation=allocation,
                medicine=allocation.medicine,
                batch=batch,
                requested_quantity=quantity,
                unit_code=allocation.unit_code,
            )

            # Prevent this optimization allocation from being
            # reused to create another transfer request.
            allocation.status = "ACCEPTED"
            allocation.save(update_fields=["status"])

        record_transfer_audit(
            user=user,
            action="TRANSFER_CREATED_FROM_OPTIMIZATION",
            transfer=transfer,
            description=(
                "Transfer request created from an optimization run."
            ),
            metadata={
                "optimization_run": str(run.pk),
                "allocation_count": len(items),
            },
        )

        created_requests.append(transfer)

    return created_requests


def get_transfer_approval_stages(transfer):
    return list(
        TransferApprovalStage.objects.filter(
            organization=transfer.organization,
            is_active=True,
        ).order_by("level")
    )


@transaction.atomic
def submit_transfer_for_approval(
    *,
    transfer_id,
    user,
):
    transfer = (
        TransferRequest.objects
        .select_for_update()
        .get(pk=transfer_id)
    )

    if transfer.status != TransferStatus.DRAFT:
        raise ValidationError(
            "Only draft transfer requests can be submitted."
        )

    if transfer.requested_by_id != user.pk and not user.is_superuser:
        raise ValidationError(
            "Only the requester or an authorized administrator "
            "can submit this transfer."
        )

    lines = list(
        transfer.lines.select_related(
            "batch",
            "batch__warehouse",
        )
    )

    if not lines:
        raise ValidationError(
            "A transfer request must contain at least one line."
        )

    stages = get_transfer_approval_stages(transfer)

    if not stages:
        raise ValidationError(
            "No active transfer approval stages are configured "
            "for this organization."
        )

    for line in lines:

        validate_transfer_batch(
            donor_facility=transfer.donor_facility,
            medicine=line.medicine,
            batch=line.batch,
            quantity=line.requested_quantity,
        )

        line.approved_quantity = line.requested_quantity
        line.save(update_fields=["approved_quantity"])

    transfer.status = TransferStatus.SUBMITTED
    transfer.current_approval_level = stages[0].level
    transfer.submitted_at = timezone.now()

    transfer.save(
        update_fields=[
            "status",
            "current_approval_level",
            "submitted_at",
            "updated_at",
        ]
    )

    record_transfer_audit(
        user=user,
        action="TRANSFER_SUBMITTED",
        transfer=transfer,
        description="Transfer request submitted for approval.",
        metadata={
            "approval_stage": stages[0].name,
            "approval_level": stages[0].level,
        },
    )

    return transfer



def user_has_transfer_approval_role(
    *,
    user,
    transfer,
    stage,
):
    if user.is_superuser:
        return True

    from apps.accounts.services import user_has_permission

    has_permission = user_has_permission(
        user,
        "redistribution.transfer.approve",
        organization=transfer.organization,
    )

    if not has_permission:
        return False

    today = timezone.localdate()

    assignments = user.role_assignments.filter(
        is_active=True,
        role__is_active=True,
        role__code=stage.required_role_code,
    ).filter(
        Q(valid_from__isnull=True)
        | Q(valid_from__lte=today)
    ).filter(
        Q(valid_until__isnull=True)
        | Q(valid_until__gte=today)
    )

    return assignments.exists()


@transaction.atomic
def approve_transfer(
    *,
    transfer_id,
    user,
    comments="",
):
    transfer = (
        TransferRequest.objects
        .select_for_update()
        .get(pk=transfer_id)
    )

    if transfer.status not in [
        TransferStatus.SUBMITTED,
        TransferStatus.IN_APPROVAL,
    ]:
        raise ValidationError(
            "This transfer is not awaiting approval."
        )

    if transfer.requested_by_id == user.pk:
        raise ValidationError(
            "The requester cannot approve their own transfer."
        )

    stage = (
        TransferApprovalStage.objects
        .filter(
            organization=transfer.organization,
            level=transfer.current_approval_level,
            is_active=True,
        )
        .first()
    )

    if not stage:
        raise ValidationError(
            "The current approval stage is missing or inactive."
        )

    if not user_has_transfer_approval_role(
        user=user,
        transfer=transfer,
        stage=stage,
    ):
        raise ValidationError(
            "You do not have the required approval role."
        )

    if TransferApprovalDecision.objects.filter(
        transfer=transfer,
        stage=stage,
    ).exists():
        raise ValidationError(
            "A decision has already been recorded for this stage."
        )

    TransferApprovalDecision.objects.create(
        transfer=transfer,
        stage=stage,
        decision=TransferApprovalDecisionType.APPROVED,
        decided_by=user,
        comments=comments,
    )

    stages = get_transfer_approval_stages(transfer)

    next_stage = next(
        (
            item
            for item in stages
            if item.level > stage.level
        ),
        None,
    )

    if next_stage:

        transfer.status = TransferStatus.IN_APPROVAL
        transfer.current_approval_level = next_stage.level

        transfer.save(
            update_fields=[
                "status",
                "current_approval_level",
                "updated_at",
            ]
        )

        record_transfer_audit(
            user=user,
            action="TRANSFER_APPROVAL_STAGE_COMPLETED",
            transfer=transfer,
            description=(
                f"Transfer approved at stage {stage.name}. "
                f"Next stage: {next_stage.name}."
            ),
            metadata={
                "completed_level": stage.level,
                "next_level": next_stage.level,
            },
        )

        return transfer

    # Final stage approved. Revalidate and reserve stock.
    reserve_transfer_stock(
        transfer=transfer,
        user=user,
    )

    transfer.status = TransferStatus.RESERVED
    transfer.approved_at = timezone.now()
    transfer.reserved_at = timezone.now()

    transfer.save(
        update_fields=[
            "status",
            "approved_at",
            "reserved_at",
            "updated_at",
        ]
    )

    record_transfer_audit(
        user=user,
        action="TRANSFER_FULLY_APPROVED_AND_RESERVED",
        transfer=transfer,
        description=(
            "All transfer approval stages completed and stock reserved."
        ),
    )

    return transfer


@transaction.atomic
def reject_transfer(
    *,
    transfer_id,
    user,
    reason,
):
    transfer = (
        TransferRequest.objects
        .select_for_update()
        .get(pk=transfer_id)
    )

    if transfer.status not in [
        TransferStatus.SUBMITTED,
        TransferStatus.IN_APPROVAL,
    ]:
        raise ValidationError(
            "Only transfers awaiting approval can be rejected."
        )

    if transfer.requested_by_id == user.pk:
        raise ValidationError(
            "The requester cannot reject their own transfer."
        )

    stage = (
        TransferApprovalStage.objects
        .filter(
            organization=transfer.organization,
            level=transfer.current_approval_level,
            is_active=True,
        )
        .first()
    )

    if not stage:
        raise ValidationError(
            "The current approval stage is missing."
        )

    if not user_has_transfer_approval_role(
        user=user,
        transfer=transfer,
        stage=stage,
    ):
        raise ValidationError(
            "You do not have the required approval role."
        )

    if not reason or not reason.strip():
        raise ValidationError(
            "A rejection reason is required."
        )

    if TransferApprovalDecision.objects.filter(
        transfer=transfer,
        stage=stage,
    ).exists():
        raise ValidationError(
            "A decision has already been recorded for this stage."
        )

    TransferApprovalDecision.objects.create(
        transfer=transfer,
        stage=stage,
        decision=TransferApprovalDecisionType.REJECTED,
        decided_by=user,
        comments=reason,
    )

    transfer.status = TransferStatus.REJECTED
    transfer.rejection_reason = reason

    transfer.save(
        update_fields=[
            "status",
            "rejection_reason",
            "updated_at",
        ]
    )

    record_transfer_audit(
        user=user,
        action="TRANSFER_REJECTED",
        transfer=transfer,
        description="Transfer request rejected.",
        metadata={"reason": reason},
    )

    return transfer


@transaction.atomic
def reserve_transfer_stock(
    *,
    transfer,
    user,
):
    if transfer.status not in [
        TransferStatus.SUBMITTED,
        TransferStatus.IN_APPROVAL,
    ]:
        raise ValidationError(
            "Transfer cannot reserve stock in its current state."
        )

    lines = list(
        transfer.lines.select_related(
            "batch",
            "batch__warehouse",
        ).order_by("batch_id")
    )

    if not lines:
        raise ValidationError(
            "Transfer has no stock lines."
        )

    for line in lines:

        quantity = (
            line.approved_quantity
            if line.approved_quantity is not None
            else line.requested_quantity
        )

        if quantity <= ZERO:
            raise ValidationError(
                "Approved quantity must be positive."
            )

        validate_transfer_batch(
            donor_facility=transfer.donor_facility,
            medicine=line.medicine,
            batch=line.batch,
            quantity=quantity,
        )

        balance = (
            InventoryBalance.objects
            .select_for_update()
            .filter(batch_id=line.batch_id)
            .first()
        )

        if balance is None:
            raise ValidationError(
                f"No inventory balance exists for batch {line.batch.batch_number}."
            )

        on_hand = Decimal(
            str(balance.quantity_on_hand)
        )

        reserved = Decimal(
            str(balance.quantity_reserved)
        )

        available = on_hand - reserved

        if available < quantity:
            raise ValidationError(
                f"Insufficient available stock for "
                f"{line.medicine.generic_name}. "
                f"Available: {available}; requested: {quantity}."
            )

        balance.quantity_reserved = reserved + quantity

        balance.save(
            update_fields=["quantity_reserved"]
        )

        line.reserved_quantity = quantity

        line.save(
            update_fields=["reserved_quantity"]
        )

    return transfer



@transaction.atomic
def cancel_transfer(
    *,
    transfer_id,
    user,
    reason,
):
    transfer = (
        TransferRequest.objects
        .select_for_update()
        .get(pk=transfer_id)
    )

    cancellable_statuses = [
        TransferStatus.DRAFT,
        TransferStatus.SUBMITTED,
        TransferStatus.IN_APPROVAL,
        TransferStatus.APPROVED,
        TransferStatus.RESERVED,
        TransferStatus.READY_FOR_DISPATCH,
    ]

    if transfer.status not in cancellable_statuses:
        raise ValidationError(
            "This transfer cannot be cancelled in its current state."
        )

    if not reason or not reason.strip():
        raise ValidationError(
            "A cancellation reason is required."
        )

    # A requester may cancel their own request.
    # Other users must have the cancellation permission.
    if (
        transfer.requested_by_id != user.pk
        and not user.is_superuser
    ):
        from apps.accounts.services import user_has_permission

        if not user_has_permission(
            user,
            "redistribution.transfer.cancel",
            organization=transfer.organization,
        ):
            raise ValidationError(
                "You are not authorized to cancel this transfer."
            )

    for line in transfer.lines.select_related("batch"):

        if line.reserved_quantity <= ZERO:
            continue

        balance = (
            InventoryBalance.objects
            .select_for_update()
            .filter(batch_id=line.batch_id)
            .first()
        )

        if balance is None:
            raise ValidationError(
                "Inventory balance missing; cannot release reservation."
            )

        reserved = Decimal(
            str(balance.quantity_reserved)
        )

        if reserved < line.reserved_quantity:
            raise ValidationError(
                "Inventory reservation is inconsistent. "
                "Manual reconciliation is required."
            )

        balance.quantity_reserved = (
            reserved - line.reserved_quantity
        )

        balance.save(
            update_fields=["quantity_reserved"]
        )

        line.reserved_quantity = ZERO

        line.save(
            update_fields=["reserved_quantity"]
        )

    transfer.status = TransferStatus.CANCELLED
    transfer.cancellation_reason = reason

    transfer.save(
        update_fields=[
            "status",
            "cancellation_reason",
            "updated_at",
        ]
    )

    record_transfer_audit(
        user=user,
        action="TRANSFER_CANCELLED",
        transfer=transfer,
        description=(
            "Transfer cancelled and any outstanding reservation released."
        ),
        metadata={"reason": reason},
    )

    return transfer


@transaction.atomic
def create_manual_transfer(
    *,
    donor_facility_id,
    recipient_facility_id,
    organization_id,
    lines,
    user,
    justification,
    priority=TransferPriority.NORMAL,
):
    from apps.organizations.models import Organization

    donor = Facility.objects.get(
        pk=donor_facility_id,
        is_active=True,
    )

    recipient = Facility.objects.get(
        pk=recipient_facility_id,
        is_active=True,
    )

    organization = Organization.objects.get(
        pk=organization_id,
    )

    if donor.pk == recipient.pk:
        raise ValidationError(
            "Donor and recipient must be different."
        )

    if not justification or not justification.strip():
        raise ValidationError(
            "A justification is required."
        )

    from apps.accounts.scope_services import (
        get_user_accessible_facility_ids,
    )

    if not user.is_superuser:

        visible_ids = set(
            get_user_accessible_facility_ids(
                user,
                permission_code="redistribution.transfer.create",
            )
        )

        if (
            donor.pk not in visible_ids
            or recipient.pk not in visible_ids
        ):
            raise ValidationError(
                "You are not authorized for both facilities."
            )

    if (
        donor.organization_id != organization.pk
        or recipient.organization_id != organization.pk
    ):
        raise ValidationError(
            "Both facilities must belong to the selected "
            "governing organization for a manual transfer."
        )

    transfer = TransferRequest.objects.create(
        source=TransferSource.MANUAL,
        donor_facility=donor,
        recipient_facility=recipient,
        organization=organization,
        requested_by=user,
        priority=priority,
        justification=justification,
        status=TransferStatus.DRAFT,
    )

    for item in lines:

        batch = StockBatch.objects.select_related(
            "warehouse",
        ).get(
            pk=item["batch_id"]
        )

        medicine_id = item["medicine_id"]

        quantity = Decimal(
            str(item["quantity"])
        )

        unit_code = item["unit_code"]

        from apps.medicines.models import Medicine

        medicine = Medicine.objects.get(
            pk=medicine_id
        )

        validate_transfer_batch(
            donor_facility=donor,
            medicine=medicine,
            batch=batch,
            quantity=quantity,
        )

        TransferRequestLine.objects.create(
            transfer=transfer,
            medicine=medicine,
            batch=batch,
            requested_quantity=quantity,
            unit_code=unit_code,
        )

    record_transfer_audit(
        user=user,
        action="MANUAL_TRANSFER_CREATED",
        transfer=transfer,
        description="Manual transfer request created.",
    )

    return transfer