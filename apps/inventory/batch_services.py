from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    BatchExpiryAlert,
    BatchLifecycleAction,
    BatchLifecycleEvent,
    BatchStatus,
    InventoryBalance,
    StockBatch,
)


def _record_lifecycle_event(
    batch,
    action,
    performed_by,
    reason,
    previous_status="",
    new_status="",
    reference_number="",
    metadata=None,
):
    return BatchLifecycleEvent.objects.create(
        batch=batch,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        reason=reason,
        reference_number=reference_number,
        performed_by=performed_by,
        metadata=metadata or {},
    )


def _change_batch_status(
    batch,
    new_status,
    action,
    performed_by,
    reason,
    reference_number="",
):
    previous_status = batch.status

    if previous_status == new_status:
        return batch

    batch.status = new_status
    batch.save(update_fields=["status", "updated_at"])

    _record_lifecycle_event(
        batch=batch,
        action=action,
        performed_by=performed_by,
        reason=reason,
        previous_status=previous_status,
        new_status=new_status,
        reference_number=reference_number,
    )

    return batch


@transaction.atomic
def quarantine_batch(
    batch_id,
    performed_by,
    reason,
    reference_number="",
):
    batch = StockBatch.objects.select_for_update().get(
        pk=batch_id
    )

    if not reason or not reason.strip():
        raise ValidationError("A quarantine reason is required.")

    if batch.status in [
        BatchStatus.DISPOSED,
        BatchStatus.RECALLED,
        BatchStatus.EXPIRED,
    ]:
        raise ValidationError(
            "This batch cannot be quarantined from its current status."
        )

    return _change_batch_status(
        batch=batch,
        new_status=BatchStatus.QUARANTINED,
        action=BatchLifecycleAction.QUARANTINED,
        performed_by=performed_by,
        reason=reason,
        reference_number=reference_number,
    )


@transaction.atomic
def release_quarantined_batch(
    batch_id,
    performed_by,
    reason,
    reference_number="",
):
    batch = StockBatch.objects.select_for_update().get(
        pk=batch_id
    )

    if batch.status != BatchStatus.QUARANTINED:
        raise ValidationError(
            "Only quarantined batches can be released."
        )

    if not reason or not reason.strip():
        raise ValidationError(
            "A release justification is required."
        )

    if batch.expiry_date < timezone.localdate():
        raise ValidationError(
            "An expired batch cannot be released for use."
        )

    return _change_batch_status(
        batch=batch,
        new_status=BatchStatus.AVAILABLE,
        action=BatchLifecycleAction.RELEASED,
        performed_by=performed_by,
        reason=reason,
        reference_number=reference_number,
    )


@transaction.atomic
def mark_batch_damaged(
    batch_id,
    performed_by,
    reason,
    reference_number="",
):
    batch = StockBatch.objects.select_for_update().get(
        pk=batch_id
    )

    if not reason or not reason.strip():
        raise ValidationError("A damage reason is required.")

    if batch.status in [
        BatchStatus.DISPOSED,
        BatchStatus.RECALLED,
        BatchStatus.EXPIRED,
    ]:
        raise ValidationError(
            "This batch cannot be marked damaged from its current status."
        )

    return _change_batch_status(
        batch=batch,
        new_status=BatchStatus.DAMAGED,
        action=BatchLifecycleAction.MARKED_DAMAGED,
        performed_by=performed_by,
        reason=reason,
        reference_number=reference_number,
    )


@transaction.atomic
def recall_batch(
    batch_id,
    performed_by,
    reason,
    reference_number,
):
    batch = StockBatch.objects.select_for_update().get(
        pk=batch_id
    )

    if not reason or not reason.strip():
        raise ValidationError("A recall reason is required.")

    if not reference_number or not reference_number.strip():
        raise ValidationError(
            "A recall reference number is required."
        )

    if batch.status == BatchStatus.DISPOSED:
        raise ValidationError(
            "A disposed batch cannot be recalled."
        )

    return _change_batch_status(
        batch=batch,
        new_status=BatchStatus.RECALLED,
        action=BatchLifecycleAction.MARKED_RECALLED,
        performed_by=performed_by,
        reason=reason,
        reference_number=reference_number,
    )


@transaction.atomic
def dispose_batch(
    batch_id,
    performed_by,
    reason,
    reference_number="",
):
    batch = StockBatch.objects.select_for_update().get(
        pk=batch_id
    )

    if batch.status not in [
        BatchStatus.QUARANTINED,
        BatchStatus.DAMAGED,
        BatchStatus.RECALLED,
        BatchStatus.EXPIRED,
    ]:
        raise ValidationError(
            "Only quarantined, damaged, recalled, or expired "
            "batches can be disposed."
        )

    if not reason or not reason.strip():
        raise ValidationError(
            "A disposal reason is required."
        )

    balance = InventoryBalance.objects.select_for_update().get(
        batch=batch
    )

    if balance.quantity_reserved > 0:
        raise ValidationError(
            "Release or cancel outstanding reservations before disposal."
        )

    if balance.quantity_on_hand > 0:
        raise ValidationError(
            "Record an authorized disposal stock movement before "
            "marking this batch as disposed."
        )

    return _change_batch_status(
        batch=batch,
        new_status=BatchStatus.DISPOSED,
        action=BatchLifecycleAction.DISPOSED,
        performed_by=performed_by,
        reason=reason,
        reference_number=reference_number,
    )


def get_expiry_level(days_remaining):
    if days_remaining < 0:
        return BatchExpiryAlert.AlertLevel.EXPIRED

    if days_remaining <= 30:
        return BatchExpiryAlert.AlertLevel.CRITICAL

    if days_remaining <= 60:
        return BatchExpiryAlert.AlertLevel.HIGH

    if days_remaining <= 90:
        return BatchExpiryAlert.AlertLevel.WARNING

    return None



@transaction.atomic
def scan_batch_expiry(thresholds=(30, 60, 90)):
    """
    Find near-expiry and expired batches.

    Creates or updates expiry alerts and automatically transitions
    expired batches to EXPIRED.

    System-generated lifecycle events are recorded with
    performed_by=None and performed_by_label="SYSTEM".

    Does not create stock movements or change stock quantities.
    """
    today = timezone.localdate()
    now = timezone.now()

    active_batches = (
        StockBatch.objects
        .select_for_update()
        .filter(
            status__in=[
                BatchStatus.AVAILABLE,
                BatchStatus.QUARANTINED,
            ]
        )
    )

    created_count = 0
    updated_count = 0
    resolved_count = 0
    expired_count = 0

    for batch in active_batches.iterator():
        days_remaining = (batch.expiry_date - today).days

        # Determine expiry alert level.
        if days_remaining < 0:
            level = BatchExpiryAlert.AlertLevel.EXPIRED
            threshold = 0
        else:
            applicable = [
                value
                for value in sorted(thresholds)
                if days_remaining <= value
            ]

            if not applicable:
                resolved_count += (
                    BatchExpiryAlert.objects.filter(
                        batch=batch,
                        is_active=True,
                    ).update(
                        is_active=False,
                        resolved_at=now,
                    )
                )
                continue

            threshold = applicable[0]
            level = get_expiry_level(days_remaining)

        # Create or retrieve the active alert.
        message = (
            f"Batch {batch.batch_number} has "
            f"{days_remaining} days remaining."
            if days_remaining >= 0
            else f"Batch {batch.batch_number} has expired."
        )

        alert, created = BatchExpiryAlert.objects.get_or_create(
            batch=batch,
            alert_level=level,
            is_active=True,
            defaults={
                "threshold_days": threshold,
                "message": message,
                "first_detected_at": now,
                "last_detected_at": now,
            },
        )

        if created:
            created_count += 1
        else:
            alert.threshold_days = threshold
            alert.last_detected_at = now
            alert.message = message

            alert.save(
                update_fields=[
                    "threshold_days",
                    "last_detected_at",
                    "message",
                ]
            )

            updated_count += 1

        # Automatically mark expired batches.
        if level == BatchExpiryAlert.AlertLevel.EXPIRED:
            expired_count += 1

            if batch.status != BatchStatus.EXPIRED:
                previous_status = batch.status

                batch.status = BatchStatus.EXPIRED

                batch.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                # Record the automated lifecycle transition.
                _record_lifecycle_event(
                    batch=batch,
                    action=BatchLifecycleAction.MARKED_EXPIRED,
                    performed_by=None,
                    reason=(
                        "Automatically marked expired by the "
                        "scheduled batch expiry scan."
                    ),
                    previous_status=previous_status,
                    new_status=BatchStatus.EXPIRED,
                    metadata={
                        "expiry_date": batch.expiry_date.isoformat(),
                        "days_remaining": days_remaining,
                        "detected_date": today.isoformat(),
                        "source": "SYSTEM_EXPIRY_SCAN",
                    },
                )

    return {
        "created_alerts": created_count,
        "updated_alerts": updated_count,
        "expired_batches_detected": expired_count,
        "resolved_alerts": resolved_count,
    }
