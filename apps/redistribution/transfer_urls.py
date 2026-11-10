from rest_framework.routers import DefaultRouter

from apps.redistribution.transfer_views import (
    TransferRequestViewSet,
    TransferApprovalStageViewSet,
)

router = DefaultRouter()

router.register(
    "requests",
    TransferRequestViewSet,
    basename="transfer-request",
)

router.register(
    "approval-stages",
    TransferApprovalStageViewSet,
    basename="transfer-approval-stage",
)

urlpatterns = router.urls