from rest_framework.routers import DefaultRouter

from apps.logistics.shipment_views import (
    ShipmentViewSet,
    TransporterViewSet,
    VehicleViewSet,
    ShipmentDocumentViewSet,
)

router = DefaultRouter()

router.register(
    "shipments",
    ShipmentViewSet,
    basename="shipment",
)

router.register(
    "transporters",
    TransporterViewSet,
    basename="transporter",
)

router.register(
    "vehicles",
    VehicleViewSet,
    basename="vehicle",
)

router.register(
    "shipment-documents",
    ShipmentDocumentViewSet,
    basename="shipment-document",
)

urlpatterns = router.urls