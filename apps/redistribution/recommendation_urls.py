from rest_framework.routers import DefaultRouter

from apps.redistribution.recommendation_views import (
    RedistributionRecommendationViewSet,
)

router = DefaultRouter()

router.register(
    "",
    RedistributionRecommendationViewSet,
    basename="redistribution-recommendation",
)

urlpatterns = router.urls
