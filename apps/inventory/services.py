from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, ExpressionWrapper, DecimalField
from django.utils import timezone

from apps.audit.services import record_audit_event

from datetime import timedelta

from apps.inventory.models import (
    BatchStatus,
    InventoryBalance,
    MovementType,
    ReservationStatus,
    StockBatch,
    StockMovement,
    StockReservation,
    StockStatus,
)

INCREASE_TYPES = {
    MovementType.RECEIPT,
    MovementType.ADJUSTMENT_IN,
    MovementType.TRANSFER_IN,
}

DECREASE_TYPES = {
    MovementType.ISSUE,
    MovementType.ADJUSTMENT_OUT,
    MovementType.TRANSFER_OUT,
    MovementType.DAMAGE,
    MovementType.EXPIRY,
}


def validate_batch_for_issue(batch):
    if batch.status != BatchStatus.AVAILABLE:
        raise ValidationError(
            f"Batch {batch.batch_number} is not available for issuing. "
            f"Current status: {batch.status}."
        )

    if batch.expiry_date < timezone.localdate():
        raise ValidationError(
            f"Batch {batch.batch_number} has expired and cannot be issued."
        )


def _audit_inventory(
    *,
    request,
    action,
    batch,
    description,
    changes=None,
):
    if request is None:
        return

    record_audit_event(
        request=request,
        category="SYSTEM",
        action=action,
        target_type="StockBatch",
        target_id=str(batch.pk),
        description=description,
        changes=changes or {},
        organization=batch.warehouse.organization,
    )


def _get_or_create_balance(batch):
    balance, _ = InventoryBalance.objects.get_or_create(
        batch=batch,
    )

    return balance


@transaction.atomic
def receive_stock(
    *,
    batch_id,
    quantity,
    performed_by,
    reference_number="",
    notes="",
    request=None,
):
    quantity = Decimal(str(quantity))

    if quantity <= 0:
        raise ValidationError("Receipt quantity must be positive.")

    batch = (
        StockBatch.objects.select_for_update()
        .select_related(
            "warehouse",
            "warehouse__organization",
        )
        .get(pk=batch_id)
    )

    if batch.status != StockStatus.AVAILABLE:
        raise ValidationError("Stock can only be received into an available batch.")

    if batch.is_expired:
        raise ValidationError("Cannot receive an expired batch.")

    balance = _get_or_create_balance(batch)

    balance = InventoryBalance.objects.select_for_update().get(pk=balance.pk)

    movement = StockMovement.objects.create(
        batch=batch,
        movement_type=MovementType.RECEIPT,
        quantity=quantity,
        reference_number=reference_number,
        reference_type="RECEIPT",
        destination_warehouse=batch.warehouse,
        notes=notes,
        performed_by=performed_by,
    )

    balance.quantity_on_hand = balance.quantity_on_hand + quantity

    balance.last_movement_at = timezone.now()

    balance.save()

    _audit_inventory(
        request=request,
        action="STOCK_RECEIVED",
        batch=batch,
        description=f"Received {quantity} units of batch {batch.batch_number}.",
        changes={"quantity_received": str(quantity)},
    )

    return movement


@transaction.atomic
def issue_stock(
    *,
    batch_id,
    quantity,
    performed_by,
    reference_number="",
    notes="",
    request=None,
):
    quantity = Decimal(str(quantity))

    if quantity <= 0:
        raise ValidationError("Issue quantity must be positive.")

    batch = (
        StockBatch.objects.select_for_update()
        .select_related(
            "warehouse",
            "warehouse__organization",
        )
        .get(pk=batch_id)
    )

    validate_batch_for_issue(batch)

    balance = _get_or_create_balance(batch)

    balance = InventoryBalance.objects.select_for_update().get(pk=balance.pk)

    if balance.quantity_available < quantity:
        raise ValidationError(
            f"Insufficient available stock. " f"Available: {balance.quantity_available}"
        )

    movement = StockMovement.objects.create(
        batch=batch,
        movement_type=MovementType.ISSUE,
        quantity=quantity,
        reference_number=reference_number,
        reference_type="ISSUE",
        source_warehouse=batch.warehouse,
        notes=notes,
        performed_by=performed_by,
    )

    balance.quantity_on_hand -= quantity
    balance.last_movement_at = timezone.now()
    balance.save()

    _audit_inventory(
        request=request,
        action="STOCK_ISSUED",
        batch=batch,
        description=f"Issued {quantity} units of batch {batch.batch_number}.",
        changes={"quantity_issued": str(quantity)},
    )

    return movement


@transaction.atomic
def adjust_stock(
    *,
    batch_id,
    quantity,
    direction,
    performed_by,
    reason,
    reference_number="",
    request=None,
):
    quantity = Decimal(str(quantity))

    if quantity <= 0:
        raise ValidationError("Adjustment quantity must be positive.")

    if direction not in ["IN", "OUT"]:
        raise ValidationError("Direction must be IN or OUT.")

    if not reason.strip():
        raise ValidationError("An adjustment reason is required.")

    batch = (
        StockBatch.objects.select_for_update()
        .select_related(
            "warehouse",
            "warehouse__organization",
        )
        .get(pk=batch_id)
    )

    balance = _get_or_create_balance(batch)

    balance = InventoryBalance.objects.select_for_update().get(pk=balance.pk)

    if direction == "IN":
        movement_type = MovementType.ADJUSTMENT_IN

        balance.quantity_on_hand += quantity

    else:
        movement_type = MovementType.ADJUSTMENT_OUT

        if balance.quantity_available < quantity:
            raise ValidationError("Adjustment would reduce available stock below zero.")

        balance.quantity_on_hand -= quantity

    movement = StockMovement.objects.create(
        batch=batch,
        movement_type=movement_type,
        quantity=quantity,
        reference_number=reference_number,
        reference_type="ADJUSTMENT",
        notes=reason,
        performed_by=performed_by,
    )

    balance.last_movement_at = timezone.now()
    balance.save()

    _audit_inventory(
        request=request,
        action="STOCK_ADJUSTED",
        batch=batch,
        description=f"Stock adjustment {direction}: {reason}",
        changes={
            "direction": direction,
            "quantity": str(quantity),
            "reason": reason,
        },
    )

    return movement


@transaction.atomic
def reserve_stock(
    *,
    batch_id,
    quantity,
    reference_number,
    reserved_by,
    purpose="",
    expires_at=None,
):
    quantity = Decimal(str(quantity))

    if quantity <= 0:
        raise ValidationError("Reservation quantity must be positive.")

    if not reference_number.strip():
        raise ValidationError("Reference number is required.")

    batch = StockBatch.objects.select_for_update().get(pk=batch_id)

    if batch.status != StockStatus.AVAILABLE or batch.is_expired:
        raise ValidationError("This batch cannot be reserved.")

    balance = _get_or_create_balance(batch)

    balance = InventoryBalance.objects.select_for_update().get(pk=balance.pk)

    if balance.quantity_available < quantity:
        raise ValidationError(
            f"Insufficient available stock. " f"Available: {balance.quantity_available}"
        )

    reservation = StockReservation.objects.create(
        batch=batch,
        quantity=quantity,
        reference_number=reference_number,
        purpose=purpose,
        reserved_by=reserved_by,
        expires_at=expires_at,
    )

    balance.quantity_reserved += quantity
    balance.save()

    return reservation


@transaction.atomic
def release_reservation(*, reservation_id):
    reservation = StockReservation.objects.select_for_update().get(pk=reservation_id)

    if reservation.status != ReservationStatus.ACTIVE:
        raise ValidationError("Only active reservations can be released.")

    balance = InventoryBalance.objects.select_for_update().get(batch=reservation.batch)

    balance.quantity_reserved -= reservation.quantity
    balance.save()

    reservation.status = ReservationStatus.RELEASED
    reservation.save(update_fields=["status", "updated_at"])

    return reservation


@transaction.atomic
def fulfill_reservation(
    *,
    reservation_id,
    performed_by,
    request=None,
):
    reservation = StockReservation.objects.select_for_update().get(pk=reservation_id)

    if reservation.status != ReservationStatus.ACTIVE:
        raise ValidationError("Only active reservations can be fulfilled.")

    if reservation.expires_at and reservation.expires_at <= timezone.now():
        raise ValidationError("This reservation has expired.")

    batch = StockBatch.objects.select_for_update().get(pk=reservation.batch_id)

    validate_batch_for_issue(batch)

    balance = InventoryBalance.objects.select_for_update().get(batch=batch)

    if balance.quantity_on_hand < reservation.quantity:
        raise ValidationError("Insufficient physical stock to fulfill reservation.")

    movement = StockMovement.objects.create(
        batch=batch,
        movement_type=MovementType.ISSUE,
        quantity=reservation.quantity,
        reference_number=reservation.reference_number,
        reference_type="RESERVATION",
        source_warehouse=batch.warehouse,
        notes=reservation.purpose,
        performed_by=performed_by,
    )

    balance.quantity_on_hand -= reservation.quantity
    balance.quantity_reserved -= reservation.quantity
    balance.last_movement_at = timezone.now()
    balance.save()

    reservation.status = ReservationStatus.FULFILLED
    reservation.save(update_fields=["status", "updated_at"])

    _audit_inventory(
        request=request,
        action="STOCK_RESERVATION_FULFILLED",
        batch=batch,
        description=(f"Reservation {reservation.reference_number} fulfilled."),
        changes={"quantity": str(reservation.quantity)},
    )

    return movement


def get_stock_balance(batch):
    balance = getattr(batch, "balance", None)

    if balance is None:
        return {
            "on_hand": Decimal("0"),
            "reserved": Decimal("0"),
            "available": Decimal("0"),
        }

    return {
        "on_hand": balance.quantity_on_hand,
        "reserved": balance.quantity_reserved,
        "available": balance.quantity_available,
    }


def get_fefo_batches(
    medicine_id,
    warehouse_id,
    presentation_id=None,
):
    today = timezone.localdate()

    queryset = (
        StockBatch.objects.filter(
            medicine_id=medicine_id,
            warehouse_id=warehouse_id,
            status=BatchStatus.AVAILABLE,
            expiry_date__gte=today,
            balance__quantity_on_hand__gt=0,
        )
        .annotate(
            available_quantity=ExpressionWrapper(
                F("balance__quantity_on_hand") - F("balance__quantity_reserved"),
                output_field=DecimalField(
                    max_digits=16,
                    decimal_places=3,
                ),
            )
        )
        .filter(available_quantity__gt=0)
    )

    if presentation_id:
        queryset = queryset.filter(presentation_id=presentation_id)

    return queryset.order_by(
        "expiry_date",
        "received_date",
        "batch_number",
    )


def get_expiring_batches(*, warehouse_id=None, days=90):
    today = timezone.localdate()
    cutoff = today + timedelta(days=days)

    queryset = StockBatch.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=cutoff,
        status=StockStatus.AVAILABLE,
    ).select_related("medicine", "warehouse", "balance")

    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)

    return queryset.order_by("expiry_date")
