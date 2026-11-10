from rest_framework.routers import DefaultRouter

from apps.logistics.receiving_views import (
    ReceivingRecordViewSet,
    ReceivingDiscrepancyViewSet,
)

router = DefaultRouter()

router.register(
    "receipts",
    ReceivingRecordViewSet,
    basename="receiving-record",
)

router.register(
    "receiving-discrepancies",
    ReceivingDiscrepancyViewSet,
    basename="receiving-discrepancy",
)

urlpatterns = router.urls