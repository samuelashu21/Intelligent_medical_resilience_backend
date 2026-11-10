from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
    StockCount,
    StockCountLine,
    StockCountStatus,
    StockReconciliation,
)

from apps.inventory.services import adjust_stock


def _require_reason(reason):
    if not reason or not reason.strip():
        raise ValidationError("A reason is required.")


@transaction.atomic
def create_stock_count(
    warehouse_id,
    reference_number,
    created_by,
    count_method="FULL",
    notes="",
):
    if not reference_number or not reference_number.strip():
        raise ValidationError("A reference number is required.")

    if StockCount.objects.filter(reference_number=reference_number).exists():
        raise ValidationError("This stock count reference number already exists.")

    stock_count = StockCount.objects.create(
        warehouse_id=warehouse_id,
        reference_number=reference_number.strip(),
        count_method=count_method,
        created_by=created_by,
        notes=notes,
    )

    # Capture the balance snapshot when the count is created.
    balances = InventoryBalance.objects.filter(
        batch__warehouse_id=warehouse_id,
    ).select_related("batch")

    lines = []

    for balance in balances.iterator():
        lines.append(
            StockCountLine(
                stock_count=stock_count,
                batch=balance.batch,
                system_quantity=balance.quantity_on_hand,
            )
        )

    StockCountLine.objects.bulk_create(lines)

    return stock_count


@transaction.atomic
def start_stock_count(stock_count_id):
    stock_count = StockCount.objects.select_for_update().get(pk=stock_count_id)

    if stock_count.status != StockCountStatus.DRAFT:
        raise ValidationError("Only draft stock counts can be started.")

    stock_count.status = StockCountStatus.IN_PROGRESS
    stock_count.started_at = timezone.now()

    stock_count.save(
        update_fields=[
            "status",
            "started_at",
            "updated_at",
        ]
    )

    return stock_count


@transaction.atomic
def record_physical_count(
    line_id,
    physical_quantity,
    counted_by,
    reason="",
    explanation="",
):
    if physical_quantity is None:
        raise ValidationError("A physical quantity is required.")

    physical_quantity = Decimal(str(physical_quantity))

    if physical_quantity < 0:
        raise ValidationError("Physical quantity cannot be negative.")

    line = (
        StockCountLine.objects.select_for_update()
        .select_related(
            "stock_count",
            "batch",
        )
        .get(pk=line_id)
    )

    if line.stock_count.status != StockCountStatus.IN_PROGRESS:
        raise ValidationError(
            "Physical counts can only be recorded during an active count."
        )

    variance = physical_quantity - line.system_quantity

    if variance != 0 and not reason:
        raise ValidationError("A variance reason is required when quantities differ.")

    line.physical_quantity = physical_quantity
    line.variance = variance
    line.reason = reason
    line.explanation = explanation
    line.counted_by = counted_by
    line.counted_at = timezone.now()

    line.save()

    return line


@transaction.atomic
def submit_stock_count(stock_count_id, submitted_by):
    stock_count = StockCount.objects.select_for_update().get(pk=stock_count_id)

    if stock_count.status != StockCountStatus.IN_PROGRESS:
        raise ValidationError("Only an active stock count can be submitted.")

    if stock_count.created_by_id == submitted_by.pk:
        # The creator may submit the count, but must not approve it.
        pass

    incomplete = stock_count.lines.filter(physical_quantity__isnull=True).exists()

    if incomplete:
        raise ValidationError("Every stock count line must have a physical count.")

    stock_count.status = StockCountStatus.SUBMITTED
    stock_count.submitted_by = submitted_by
    stock_count.submitted_at = timezone.now()

    stock_count.save(
        update_fields=[
            "status",
            "submitted_by",
            "submitted_at",
            "updated_at",
        ]
    )

    return stock_count


@transaction.atomic
def approve_stock_count(stock_count_id, approved_by):
    stock_count = StockCount.objects.select_for_update().get(pk=stock_count_id)

    if stock_count.status not in [
        StockCountStatus.SUBMITTED,
        StockCountStatus.UNDER_REVIEW,
    ]:
        raise ValidationError("Only submitted stock counts can be approved.")

    if stock_count.created_by_id == approved_by.pk:
        raise ValidationError("The person who created the count cannot approve it.")

    if stock_count.submitted_by_id == approved_by.pk:
        raise ValidationError("The person who submitted the count cannot approve it.")

    stock_count.status = StockCountStatus.APPROVED
    stock_count.approved_by = approved_by
    stock_count.approved_at = timezone.now()

    stock_count.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    return stock_count


@transaction.atomic
def reject_stock_count(stock_count_id, rejected_by, reason):
    _require_reason(reason)

    stock_count = StockCount.objects.select_for_update().get(pk=stock_count_id)

    if stock_count.status not in [
        StockCountStatus.SUBMITTED,
        StockCountStatus.UNDER_REVIEW,
    ]:
        raise ValidationError("Only submitted counts can be rejected.")

    if stock_count.created_by_id == rejected_by.pk:
        raise ValidationError("The count creator cannot reject their own submission.")

    stock_count.status = StockCountStatus.REJECTED
    stock_count.notes = f"{stock_count.notes}\nRejection: {reason}".strip()

    stock_count.save(update_fields=["status", "notes", "updated_at"])

    return stock_count


@transaction.atomic
def post_stock_reconciliation(
    stock_count_id,
    posted_by,
):
    stock_count = StockCount.objects.select_for_update().get(pk=stock_count_id)

    if stock_count.status != StockCountStatus.APPROVED:
        raise ValidationError("Only approved stock counts can be posted.")

    if stock_count.created_by_id == posted_by.pk:
        raise ValidationError("The count creator cannot post their own reconciliation.")

    if stock_count.approved_by_id == posted_by.pk:
        raise ValidationError("The approver cannot post their own reconciliation.")

    lines = list(stock_count.lines.select_related("batch").order_by("batch_id"))

    for line in lines:
        if line.physical_quantity is None:
            raise ValidationError(
                f"Batch {line.batch.batch_number} has no physical count."
            )

        if line.variance == 0:
            continue

        if not line.reason:
            raise ValidationError(
                f"Batch {line.batch.batch_number} requires a variance reason."
            )

        balance = InventoryBalance.objects.select_for_update().get(batch=line.batch)

        # Do not apply a stale count against a balance that changed
        # after the original system snapshot was captured.
        if balance.quantity_on_hand != line.system_quantity:
            raise ValidationError(
                f"Stock for batch {line.batch.batch_number} changed "
                "after the count snapshot. Recount this batch before posting."
            )

        # Never reconcile by removing reserved stock.
        if line.variance < 0:
            reduction = abs(line.variance)

            if reduction > balance.quantity_available:
                raise ValidationError(
                    f"Variance for {line.batch.batch_number} exceeds "
                    "available stock. Resolve reservations first."
                )

        movement = adjust_stock(
            batch_id=line.batch_id,
            quantity=abs(line.variance),
            direction="IN" if line.variance > 0 else "OUT",
            performed_by=posted_by,
            reason=(
                f"Stock reconciliation {stock_count.reference_number}: "
                f"{line.explanation or line.reason}"
            ),
        )

        StockReconciliation.objects.create(
            stock_count=stock_count,
            count_line=line,
            system_quantity=line.system_quantity,
            physical_quantity=line.physical_quantity,
            variance=line.variance,
            adjustment_movement=movement,
            reason=line.reason,
            explanation=line.explanation,
            posted_by=posted_by,
            posted_at=timezone.now(),
        )

    stock_count.status = StockCountStatus.POSTED
    stock_count.posted_at = timezone.now()

    stock_count.save(update_fields=["status", "posted_at", "updated_at"])

    return stock_count
