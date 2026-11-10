from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.replenishment.approval_views import (
    ApprovalDecisionViewSet,
    ApprovalWorkflowViewSet,
    ReplenishmentApprovalViewSet,
)


router = DefaultRouter()

router.register(
    "workflows",
    ApprovalWorkflowViewSet,
    basename="approval-workflow",
)

router.register(
    "stages",
    ReplenishmentApprovalViewSet,
    basename="replenishment-approval",
)

router.register(
    "decisions",
    ApprovalDecisionViewSet,
    basename="approval-decision",
)


urlpatterns = [
    path("", include(router.urls)),
]