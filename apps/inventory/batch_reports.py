from django.db.models import Sum, Count
from django.utils import timezone

from datetime import timedelta

from apps.inventory.models import (
    BatchExpiryAlert,
    BatchStatus,
    InventoryBalance,
    StockBatch,
)


def get_batch_expiry_summary(organization_ids=None):
    today = timezone.localdate()

    batches = StockBatch.objects.all()

    if organization_ids is not None:
        batches = batches.filter(warehouse__organization_id__in=organization_ids)

    balances = InventoryBalance.objects.filter(batch__in=batches)

    expired = balances.filter(batch__expiry_date__lt=today).aggregate(
        batches=Count("id"),
        units=Sum("quantity_on_hand"),
    )

    near_30 = balances.filter(
        batch__expiry_date__gte=today,
        batch__expiry_date__lte=today + timedelta(days=30),
        batch__status=BatchStatus.AVAILABLE,
    ).aggregate(
        batches=Count("id"),
        units=Sum("quantity_available"),
    )

    near_60 = balances.filter(
        batch__expiry_date__gt=today + timedelta(days=30),
        batch__expiry_date__lte=today + timedelta(days=60),
        batch__status=BatchStatus.AVAILABLE,
    ).aggregate(
        batches=Count("id"),
        units=Sum("quantity_available"),
    )

    near_90 = balances.filter(
        batch__expiry_date__gt=today + timedelta(days=60),
        batch__expiry_date__lte=today + timedelta(days=90),
        batch__status=BatchStatus.AVAILABLE,
    ).aggregate(
        batches=Count("id"),
        units=Sum("quantity_available"),
    )

    return {
        "expired": expired,
        "expiring_within_30_days": near_30,
        "expiring_within_60_days": near_60,
        "expiring_within_90_days": near_90,
        "active_alerts": BatchExpiryAlert.objects.filter(
            batch__in=batches,
            is_active=True,
        ).count(),
    }
