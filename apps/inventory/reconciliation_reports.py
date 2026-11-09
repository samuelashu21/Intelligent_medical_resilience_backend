from decimal import Decimal

from django.db.models import Count, Sum

from apps.inventory.models import (
    StockCount,
    StockCountLine,
    StockCountStatus,
)


def get_reconciliation_summary(
    organization_ids=None,
    warehouse_id=None,
):
    counts = StockCount.objects.all()

    if organization_ids is not None:
        counts = counts.filter(
            warehouse__organization_id__in=organization_ids
        )

    if warehouse_id:
        counts = counts.filter(
            warehouse_id=warehouse_id
        )

    lines = StockCountLine.objects.filter(
        stock_count__in=counts,
        physical_quantity__isnull=False,
    )

    positive_variance = lines.filter(
        variance__gt=0
    ).aggregate(
        count=Count("id"),
        quantity=Sum("variance"),
    )

    negative_variance = lines.filter(
        variance__lt=0
    ).aggregate(
        count=Count("id"),
        quantity=Sum("variance"),
    )

    absolute_variance = sum(
        (
            abs(line.variance)
            for line in lines.iterator()
        ),
        Decimal("0"),
    )

    return {
        "total_counts": counts.count(),
        "draft_counts": counts.filter(
            status=StockCountStatus.DRAFT
        ).count(),
        "in_progress_counts": counts.filter(
            status=StockCountStatus.IN_PROGRESS
        ).count(),
        "submitted_counts": counts.filter(
            status=StockCountStatus.SUBMITTED
        ).count(),
        "approved_counts": counts.filter(
            status=StockCountStatus.APPROVED
        ).count(),
        "posted_counts": counts.filter(
            status=StockCountStatus.POSTED
        ).count(),
        "positive_variances": {
            "lines": positive_variance["count"] or 0,
            "quantity": str(
                positive_variance["quantity"] or Decimal("0")
            ),
        },
        "negative_variances": {
            "lines": negative_variance["count"] or 0,
            "quantity": str(
                negative_variance["quantity"] or Decimal("0")
            ),
        },
        "absolute_variance": str(absolute_variance),
    }