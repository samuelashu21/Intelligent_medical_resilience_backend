from rest_framework.routers import DefaultRouter

from apps.facilities.views import (
    FacilityViewSet,
    FacilityTypeViewSet,
)

router = DefaultRouter()

router.register(
    "types",
    FacilityTypeViewSet,
    basename="facility-type",
)

router.register(
    "",
    FacilityViewSet,
    basename="facility",
)

urlpatterns = router.urls