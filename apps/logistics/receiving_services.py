
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.logistics.shipment_models import (
    Shipment,
    ShipmentStatus,
    ShipmentEvent,
    ShipmentEventType,
)

from apps.logistics.receiving_models import (
    ReceivingRecord,
    ReceivingLine,
    ReceivingDiscrepancy,
    ReceivingStatus,
    DiscrepancyType,
    DiscrepancyStatus,
)

from apps.logistics.inventory_receiving_integration import (
    post_received_stock,
)

from apps.logistics.receiving_models import (
    TransferReconciliation,
    TransferReconciliationStatus,
)


ZERO = Decimal("0")


def record_receiving_audit(
    *,
    user,
    action,
    receipt,
    description,
    metadata=None,
):
    from apps.audit.services import record_audit_event

    record_audit_event(
        actor=user,
        category="SYSTEM",
        action=action,
        target_type="ReceivingRecord",
        target_id=str(receipt.pk),
        description=description,
        organization=receipt.shipment.transfer.organization,
        metadata=metadata or {},
    )


@transaction.atomic
def create_receiving_record(
    *,
    shipment_id,
    receiving_warehouse,
    user,
    notes="",
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .select_related(
            "transfer",
            "transfer__recipient_facility",
        )
        .get(pk=shipment_id)
    )

    if shipment.status != ShipmentStatus.DELIVERED:
        raise ValidationError(
            "Only delivered shipments can be received."
        )

    if ReceivingRecord.objects.filter(
        shipment=shipment
    ).exists():
        raise ValidationError(
            "A receiving record already exists for this shipment."
        )

    recipient_facility = shipment.transfer.recipient_facility

    if receiving_warehouse.facility_id != recipient_facility.pk:
        raise ValidationError(
            "Receiving warehouse must belong to the recipient facility."
        )

    if not receiving_warehouse.is_active:
        raise ValidationError(
            "Receiving warehouse is inactive."
        )

    shipment_lines = list(
        shipment.lines.select_related(
            "medicine",
            "batch",
        )
    )

    if not shipment_lines:
        raise ValidationError(
            "Cannot receive a shipment without shipment lines."
        )

    receipt = ReceivingRecord(
        shipment=shipment,
        recipient_facility=recipient_facility,
        receiving_warehouse=receiving_warehouse,
        received_by=user,
        notes=notes,
    )

    receipt.full_clean()
    receipt.save()

    for shipment_line in shipment_lines:
        ReceivingLine.objects.create(
            receiving_record=receipt,
            shipment_line=shipment_line,
            medicine=shipment_line.medicine,
            batch=shipment_line.batch,
            dispatched_quantity=shipment_line.dispatched_quantity,
            unit_code=shipment_line.unit_code,
        )

    record_receiving_audit(
        user=user,
        action="RECEIVING_RECORD_CREATED",
        receipt=receipt,
        description="Recipient receiving record created.",
        metadata={
            "shipment_id": str(shipment.pk),
            "warehouse_id": str(receiving_warehouse.pk),
        },
    )

    return receipt


@transaction.atomic
def record_received_line(
    *,
    receiving_line_id,
    physically_received_quantity,
    accepted_quantity,
    damaged_quantity=ZERO,
    expired_quantity=ZERO,
    other_rejected_quantity=ZERO,
    inspection_notes="",
    user,
):
    line = (
        ReceivingLine.objects
        .select_for_update()
        .select_related(
            "receiving_record",
            "shipment_line",
            "batch",
        )
        .get(pk=receiving_line_id)
    )

    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .get(pk=line.receiving_record_id)
    )

    if receipt.status != ReceivingStatus.DRAFT:
        raise ValidationError(
            "Only draft receiving records can be edited."
        )

    quantities = {
        "physically_received_quantity": physically_received_quantity,
        "accepted_quantity": accepted_quantity,
        "damaged_quantity": damaged_quantity,
        "expired_quantity": expired_quantity,
        "other_rejected_quantity": other_rejected_quantity,
    }

    normalized = {}

    for field, value in quantities.items():
        try:
            value = Decimal(str(value))
        except Exception:
            raise ValidationError(
                f"{field} must be a valid decimal quantity."
            )

        if value < ZERO:
            raise ValidationError(
                f"{field} cannot be negative."
            )

        normalized[field] = value

    physical = normalized["physically_received_quantity"]
    accepted = normalized["accepted_quantity"]

    if physical > line.dispatched_quantity:
        excess = physical - line.dispatched_quantity
    else:
        excess = ZERO

    if accepted > physical:
        raise ValidationError(
            "Accepted quantity cannot exceed physically received quantity."
        )

    if accepted > line.dispatched_quantity:
        raise ValidationError(
            "Accepted quantity cannot exceed dispatched quantity."
        )

    rejected = physical - accepted

    categorized_rejected = (
        normalized["damaged_quantity"]
        + normalized["expired_quantity"]
        + normalized["other_rejected_quantity"]
    )

    if categorized_rejected > rejected:
        raise ValidationError(
            "Damaged, expired and other rejected quantities "
            "cannot exceed the rejected quantity."
        )

    if (
        normalized["expired_quantity"] > ZERO
        and line.batch.expiry_date >= timezone.localdate()
    ):
        raise ValidationError(
            "An unexpired batch cannot be classified as expired."
        )

    if (
        normalized["expired_quantity"] == ZERO
        and line.batch.expiry_date < timezone.localdate()
        and accepted > ZERO
    ):
        raise ValidationError(
            "Expired medicine cannot be accepted into usable stock."
        )

    line.physically_received_quantity = physical
    line.accepted_quantity = accepted
    line.damaged_quantity = normalized["damaged_quantity"]
    line.expired_quantity = normalized["expired_quantity"]
    line.other_rejected_quantity = normalized[
        "other_rejected_quantity"
    ]
    line.inspection_notes = inspection_notes

    line.full_clean()
    line.save()

    return line


def _create_line_discrepancies(*, line, user):
    """
    Create auditable discrepancy records from the final inspection.
    Called only when a receipt is submitted.
    """

    specifications = [
        (
            DiscrepancyType.MISSING,
            line.missing_quantity,
            "Quantity dispatched but not physically received.",
        ),
        (
            DiscrepancyType.EXCESS,
            line.excess_quantity,
            "Quantity physically received above dispatched quantity.",
        ),
        (
            DiscrepancyType.DAMAGED,
            line.damaged_quantity,
            "Medicine received in damaged condition.",
        ),
        (
            DiscrepancyType.EXPIRED,
            line.expired_quantity,
            "Medicine received expired.",
        ),
        (
            DiscrepancyType.OTHER,
            line.other_rejected_quantity,
            "Other rejected quantity.",
        ),
    ]

    for discrepancy_type, quantity, description in specifications:
        if quantity > ZERO:
            ReceivingDiscrepancy.objects.create(
                receiving_line=line,
                discrepancy_type=discrepancy_type,
                quantity=quantity,
                description=(
                    f"{description} "
                    f"Inspection notes: {line.inspection_notes}"
                ),
                reported_by=user,
            )


@transaction.atomic
def submit_receiving_record(
    *,
    receiving_record_id,
    user,
):
    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .get(pk=receiving_record_id)
    )

    if receipt.status != ReceivingStatus.DRAFT:
        raise ValidationError(
            "Only draft receiving records can be submitted."
        )

    lines = list(
        receipt.lines.select_for_update().select_related(
            "batch",
            "shipment_line",
        )
    )

    if not lines:
        raise ValidationError(
            "A receiving record must contain at least one line."
        )

    for line in lines:
        line.full_clean()

        if line.physically_received_quantity < ZERO:
            raise ValidationError(
                "Physical received quantity cannot be negative."
            )

        _create_line_discrepancies(
            line=line,
            user=user,
        )

    receipt.status = ReceivingStatus.SUBMITTED
    receipt.submitted_by = user
    receipt.submitted_at = timezone.now()

    receipt.save(
        update_fields=[
            "status",
            "submitted_by",
            "submitted_at",
            "updated_at",
        ]
    )

    record_receiving_audit(
        user=user,
        action="RECEIVING_RECORD_SUBMITTED",
        receipt=receipt,
        description="Receiving record submitted for approval.",
        metadata={
            "line_count": len(lines),
        },
    )

    return receipt


@transaction.atomic
def approve_receiving_record(
    *,
    receiving_record_id,
    user,
):
    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .get(pk=receiving_record_id)
    )

    if receipt.status != ReceivingStatus.SUBMITTED:
        raise ValidationError(
            "Only submitted receiving records can be approved."
        )

    if receipt.received_by_id == user.pk:
        raise ValidationError(
            "The receiving record creator cannot approve their own record."
        )

    if receipt.submitted_by_id == user.pk:
        raise ValidationError(
            "The submitter cannot approve their own receiving record."
        )

    # Both open and under-review discrepancies must be reviewed
    # before the receiving record can be approved.
    if receipt.discrepancies.filter(
        status__in=[
            DiscrepancyStatus.OPEN,
            DiscrepancyStatus.UNDER_REVIEW,
        ]
    ).exists():
        raise ValidationError(
            "Review all open discrepancies before approval."
        )

    receipt.status = ReceivingStatus.APPROVED
    receipt.approved_by = user
    receipt.approved_at = timezone.now()

    receipt.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    record_receiving_audit(
        user=user,
        action="RECEIVING_RECORD_APPROVED",
        receipt=receipt,
        description="Receiving record approved.",
    )

    return receipt


@transaction.atomic
def reject_receiving_record(
    *,
    receiving_record_id,
    user,
    reason,
):
    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .get(pk=receiving_record_id)
    )

    if receipt.status != ReceivingStatus.SUBMITTED:
        raise ValidationError(
            "Only submitted receiving records can be rejected."
        )

    if not reason or not reason.strip():
        raise ValidationError(
            "A rejection reason is required."
        )

    receipt.status = ReceivingStatus.REJECTED
    receipt.approved_by = user
    receipt.rejection_reason = reason
    receipt.approved_at = timezone.now()

    receipt.save(
        update_fields=[
            "status",
            "approved_by",
            "rejection_reason",
            "approved_at",
            "updated_at",
        ]
    )

    record_receiving_audit(
        user=user,
        action="RECEIVING_RECORD_REJECTED",
        receipt=receipt,
        description=reason,
    )

    return receipt


@transaction.atomic
def post_receiving_record(
    *,
    receiving_record_id,
    user,
):
    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .select_related(
            "receiving_warehouse",
            "shipment",
        )
        .get(pk=receiving_record_id)
    )

    if receipt.status != ReceivingStatus.APPROVED:
        raise ValidationError(
            "Only approved receiving records can be posted."
        )

    if receipt.posted_at is not None:
        raise ValidationError(
            "This receiving record has already been posted."
        )

    lines = list(
        receipt.lines.select_for_update().select_related(
            "medicine",
            "batch",
            "shipment_line",
        ).order_by("batch_id", "pk")
    )

    if not lines:
        raise ValidationError(
            "There are no receiving lines to post."
        )

    posted_lines = []

    for line in lines:
        if line.accepted_quantity <= ZERO:
            continue

        if line.batch.expiry_date < timezone.localdate():
            raise ValidationError(
                "Expired stock cannot be posted as usable stock."
            )

        movement = post_received_stock(
            receiving_line=line,
            quantity=line.accepted_quantity,
            receiving_warehouse=receipt.receiving_warehouse,
            user=user,
            receiving_record=receipt,
        )

        posted_lines.append({
            "receiving_line_id": str(line.pk),
            "movement_id": str(movement.pk),
            "quantity": str(line.accepted_quantity),
        })

    receipt.status = ReceivingStatus.POSTED
    receipt.posted_by = user
    receipt.posted_at = timezone.now()

    receipt.save(
        update_fields=[
            "status",
            "posted_by",
            "posted_at",
            "updated_at",
        ]
    )

    ShipmentEvent.objects.create(
        shipment=receipt.shipment,
        event_type=ShipmentEventType.RECEIVED,
        description=(
            "Recipient accepted and posted the verified "
            "quantities into inventory."
        ),
        recorded_by=user,
    )

    record_receiving_audit(
        user=user,
        action="RECEIVING_RECORD_POSTED",
        receipt=receipt,
        description="Accepted recipient stock posted to inventory.",
        metadata={
            "posted_lines": posted_lines,
        },
    )

    return receipt


@transaction.atomic
def resolve_receiving_discrepancy(
    *,
    discrepancy_id,
    user,
    resolution_notes,
    decision,
):
    discrepancy = (
        ReceivingDiscrepancy.objects
        .select_for_update()
        .select_related(
            "receiving_line",
            "receiving_line__receiving_record",
        )
        .get(pk=discrepancy_id)
    )

    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .get(pk=discrepancy.receiving_line.receiving_record_id)
    )

    if receipt.status != ReceivingStatus.SUBMITTED:
        raise ValidationError(
            "Discrepancies can only be resolved while the receipt is submitted."
        )

    if discrepancy.status in [
        DiscrepancyStatus.ACCEPTED,
        DiscrepancyStatus.REJECTED,
        DiscrepancyStatus.RESOLVED,
    ]:
        raise ValidationError(
            "This discrepancy has already been resolved."
        )

    if decision not in [
        DiscrepancyStatus.ACCEPTED,
        DiscrepancyStatus.REJECTED,
    ]:
        raise ValidationError(
            "Decision must be ACCEPTED or REJECTED."
        )

    if not resolution_notes or not resolution_notes.strip():
        raise ValidationError(
            "Resolution notes are required."
        )

    discrepancy.status = decision
    discrepancy.resolution_notes = resolution_notes
    discrepancy.resolved_by = user
    discrepancy.resolved_at = timezone.now()

    discrepancy.save(
        update_fields=[
            "status",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
        ]
    )

    record_receiving_audit(
        user=user,
        action="RECEIVING_DISCREPANCY_RESOLVED",
        receipt=receipt,
        description=resolution_notes,
        metadata={
            "discrepancy_id": str(discrepancy.pk),
            "decision": decision,
            "quantity": str(discrepancy.quantity),
        },
    )

    return discrepancy




@transaction.atomic
def reconcile_transfer_receipt(
    *,
    receiving_record_id,
    user,
    notes="",
):
    receipt = (
        ReceivingRecord.objects
        .select_for_update()
        .select_related("shipment__transfer")
        .get(pk=receiving_record_id)
    )

    if receipt.status != ReceivingStatus.POSTED:
        raise ValidationError(
            "Only posted receiving records can be reconciled."
        )

    if TransferReconciliation.objects.filter(
        receiving_record=receipt
    ).exists():
        raise ValidationError(
            "This receipt has already been reconciled."
        )

    lines = list(
        receipt.lines.select_for_update()
    )

    dispatched = sum(
        (line.dispatched_quantity for line in lines),
        ZERO,
    )

    physically_received = sum(
        (line.physically_received_quantity for line in lines),
        ZERO,
    )

    accepted = sum(
        (line.accepted_quantity for line in lines),
        ZERO,
    )

    missing = sum(
        (line.missing_quantity for line in lines),
        ZERO,
    )

    excess = sum(
        (line.excess_quantity for line in lines),
        ZERO,
    )

    rejected = sum(
        (line.rejected_quantity for line in lines),
        ZERO,
    )

    if missing == ZERO and excess == ZERO and rejected == ZERO:
        reconciliation_status = (
            TransferReconciliationStatus.COMPLETE
        )
    elif missing > ZERO or excess > ZERO:
        reconciliation_status = (
            TransferReconciliationStatus.DISCREPANCY
        )
    else:
        reconciliation_status = (
            TransferReconciliationStatus.PARTIAL
        )

    reconciliation = TransferReconciliation.objects.create(
        transfer=receipt.shipment.transfer,
        receiving_record=receipt,
        dispatched_quantity_total=dispatched,
        physically_received_quantity_total=physically_received,
        accepted_quantity_total=accepted,
        missing_quantity_total=missing,
        excess_quantity_total=excess,
        rejected_quantity_total=rejected,
        status=reconciliation_status,
        reconciled_by=user,
        notes=notes,
    )

    record_shipment_audit(
        user=user,
        action="TRANSFER_RECEIPT_RECONCILED",
        receipt=receipt,
        description="Transfer receipt reconciled.",
        metadata={
            "reconciliation_id": str(reconciliation.pk),
            "status": reconciliation_status,
            "dispatched": str(dispatched),
            "accepted": str(accepted),
            "missing": str(missing),
            "excess": str(excess),
            "rejected": str(rejected),
        },
    )

    return reconciliation