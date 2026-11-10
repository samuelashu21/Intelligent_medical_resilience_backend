from rest_framework.routers import DefaultRouter

from apps.medicines.views import (
    AdministrationRouteViewSet,
    DosageFormViewSet,
    MeasurementUnitViewSet,
    MedicineViewSet,
    TherapeuticCategoryViewSet,
)
from apps.medicines.classification_views import (
    ATCClassificationViewSet,
    CountryViewSet,
    CurrentEssentialMedicinesViewSet,
    EssentialMedicineItemViewSet,
    EssentialMedicineListViewSet,
    MedicineEligibilityRuleViewSet,
    MedicineNationalCodeViewSet,
    MedicinePresentationViewSet,
)

router = DefaultRouter()

# --- Phase 11 Registrations ---
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

# --- New Classification Registrations ---
router.register(
    "countries",
    CountryViewSet,
    basename="medicine-country",
)

router.register(
    "atc",
    ATCClassificationViewSet,
    basename="atc-classification",
)

router.register(
    "essential-lists",
    EssentialMedicineListViewSet,
    basename="essential-medicine-list",
)

router.register(
    "essential-list-items",
    EssentialMedicineItemViewSet,
    basename="essential-medicine-item",
)

router.register(
    "national-codes",
    MedicineNationalCodeViewSet,
    basename="medicine-national-code",
)

router.register(
    "presentations",
    MedicinePresentationViewSet,
    basename="medicine-presentation",
)

router.register(
    "eligibility-rules",
    MedicineEligibilityRuleViewSet,
    basename="medicine-eligibility-rule",
)

router.register(
    "current-essential-medicines",
    CurrentEssentialMedicinesViewSet,
    basename="current-essential-medicines",
)

urlpatterns = router.urls
