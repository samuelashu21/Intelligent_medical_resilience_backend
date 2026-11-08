from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    InventoryBalanceViewSet,
    InventoryReportViewSet,
    StockBatchViewSet,
    StockMovementViewSet,
    StockReservationViewSet,
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

urlpatterns = router.urls