from rest_framework.routers import DefaultRouter

from apps.suppliers.views import (
    SupplierAddressViewSet,
    SupplierContactViewSet,
    SupplierContractViewSet,
    SupplierLicenseViewSet,
    SupplierMedicineViewSet,
    SupplierPerformanceViewSet,
    SupplierViewSet,
)

router = DefaultRouter()

router.register(
    "suppliers",
    SupplierViewSet,
    basename="supplier",
)

router.register(
    "contacts",
    SupplierContactViewSet,
    basename="supplier-contact",
)

router.register(
    "addresses",
    SupplierAddressViewSet,
    basename="supplier-address",
)

router.register(
    "licenses",
    SupplierLicenseViewSet,
    basename="supplier-license",
)

router.register(
    "medicine-offerings",
    SupplierMedicineViewSet,
    basename="supplier-medicine",
)

router.register(
    "contracts",
    SupplierContractViewSet,
    basename="supplier-contract",
)

router.register(
    "performance",
    SupplierPerformanceViewSet,
    basename="supplier-performance",
)

urlpatterns = router.urls