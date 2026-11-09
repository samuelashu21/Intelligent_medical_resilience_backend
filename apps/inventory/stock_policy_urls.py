from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.stock_policy_views import (
    StockPolicyEvaluationView,
    StockPolicyViewSet,
)


router = DefaultRouter()

router.register(
    "policies",
    StockPolicyViewSet,
    basename="stock-policy",
)


urlpatterns = [
    path(
        "evaluate/",
        StockPolicyEvaluationView.as_view(),
        name="stock-policy-evaluate",
    ),
    path(
        "",
        include(router.urls),
    ),
]