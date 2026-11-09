
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    InventoryBalanceViewSet,
    InventoryReportViewSet,
    StockBatchViewSet,
    StockMovementViewSet,
    StockReservationViewSet,
)

from apps.inventory.batch_views import (
    BatchExpiryAlertViewSet,
    BatchLifecycleEventViewSet,
    BatchLifecycleViewSet,
)

from apps.inventory.reconciliation_views import (
    ReconciliationSummaryView,
    StockCountLineViewSet,
    StockCountViewSet,
    StockReconciliationViewSet,
)


router = DefaultRouter()

router.register(
    "batches",
    StockBatchViewSet,
    basename="stock-batch",
)

router.register(
    "balances",
    InventoryBalanceViewSet,
    basename="inventory-balance",
)

router.register(
    "movements",
    StockMovementViewSet,
    basename="stock-movement",
)

router.register(
    "reservations",
    StockReservationViewSet,
    basename="stock-reservation",
)

router.register(
    "reports",
    InventoryReportViewSet,
    basename="inventory-report",
)

router.register(
    "batch-lifecycle",
    BatchLifecycleViewSet,
    basename="batch-lifecycle",
)

router.register(
    "expiry-alerts",
    BatchExpiryAlertViewSet,
    basename="batch-expiry-alert",
)

router.register(
    "lifecycle-events",
    BatchLifecycleEventViewSet,
    basename="batch-lifecycle-event",
)

router.register(
    "stock-counts",
    StockCountViewSet,
    basename="stock-count",
)

router.register(
    "stock-count-lines",
    StockCountLineViewSet,
    basename="stock-count-line",
)

router.register(
    "reconciliations",
    StockReconciliationViewSet,
    basename="stock-reconciliation",
)


urlpatterns = [
    path(
        "reconciliation-summary/",
        ReconciliationSummaryView.as_view(),
        name="reconciliation-summary",
    ),
    path(
    "reports/",
    include("apps.inventory.reporting_urls"),
),

path(
    "policies/",
    include("apps.inventory.stock_policy_urls"),
),
] + router.urls
