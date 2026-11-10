from rest_framework.routers import DefaultRouter

from apps.redistribution.optimization_views import (
    RedistributionOptimizationViewSet,
    RedistributionTransportProfileViewSet,
)

router = DefaultRouter()

router.register(
    "",
    RedistributionOptimizationViewSet,
    basename="redistribution-optimization",
)

router.register(
    "transport-profiles",
    RedistributionTransportProfileViewSet,
    basename="redistribution-transport-profile",
)

urlpatterns = router.urls
