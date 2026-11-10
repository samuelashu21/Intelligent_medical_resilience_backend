from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.replenishment.views import (
    PolicyReplenishmentRequestView,
    ReplenishmentRequestViewSet,
)


router = DefaultRouter()

router.register(
    "requests",
    ReplenishmentRequestViewSet,
    basename="replenishment-request",
)


urlpatterns = [
    path(
        "requests/from-policy/",
        PolicyReplenishmentRequestView.as_view(),
        name="policy-replenishment-request",
    ),
    path(
        "",
        include(router.urls),
    ),
]