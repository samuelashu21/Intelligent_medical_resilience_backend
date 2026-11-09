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

urlpatterns = router.urls