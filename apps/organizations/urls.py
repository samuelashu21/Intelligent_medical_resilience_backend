from rest_framework.routers import DefaultRouter

from apps.organizations.views import (
    OrganizationViewSet,
    OrganizationUnitTypeViewSet,
)

router = DefaultRouter()

router.register( 
    "types",
    OrganizationUnitTypeViewSet,
    basename="organization-type",
)

router.register(
    "",
    OrganizationViewSet, 
    basename="organization",
)

urlpatterns = router.urls