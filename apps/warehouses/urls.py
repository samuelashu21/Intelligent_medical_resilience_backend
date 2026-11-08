from rest_framework.routers import DefaultRouter

from apps.warehouses.views import (
    StorageLocationViewSet,
    StorageZoneViewSet,
    WarehouseCapacityViewSet,
    WarehouseManagerViewSet,
    WarehouseTemperatureViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()

router.register(
    "warehouses",
    WarehouseViewSet,
    basename="warehouse",
)

router.register(
    "zones",
    StorageZoneViewSet,
    basename="storage-zone",
)

router.register(
    "locations",
    StorageLocationViewSet,
    basename="storage-location",
)

router.register(
    "managers",
    WarehouseManagerViewSet,
    basename="warehouse-manager",
)

router.register(
    "temperature-readings",
    WarehouseTemperatureViewSet,
    basename="warehouse-temperature",
)

router.register(
    "capacity-snapshots",
    WarehouseCapacityViewSet,
    basename="warehouse-capacity",
)

urlpatterns = router.urls