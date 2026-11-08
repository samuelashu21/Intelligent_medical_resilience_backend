from rest_framework.routers import DefaultRouter

from apps.medicines.views import (
    AdministrationRouteViewSet,
    DosageFormViewSet,
    MeasurementUnitViewSet,
    MedicineViewSet,
    TherapeuticCategoryViewSet,
)

router = DefaultRouter()

router.register(
    "catalog",
    MedicineViewSet,
    basename="medicine",
)

router.register(
    "categories",
    TherapeuticCategoryViewSet,
    basename="therapeutic-category",
)

router.register(
    "dosage-forms",
    DosageFormViewSet,
    basename="dosage-form",
)

router.register(
    "administration-routes",
    AdministrationRouteViewSet,
    basename="administration-route",
)

router.register(
    "units",
    MeasurementUnitViewSet,
    basename="measurement-unit",
)

urlpatterns = router.urls