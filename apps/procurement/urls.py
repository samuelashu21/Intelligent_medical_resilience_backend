from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.procurement.views import (
    PurchaseRequisitionViewSet,
    SupplierQuotationViewSet,
    PurchaseOrderViewSet,
)


router = DefaultRouter()

router.register(
    "requisitions",
    PurchaseRequisitionViewSet,
    basename="purchase-requisition",
)

router.register(
    "quotations",
    SupplierQuotationViewSet,
    basename="supplier-quotation",
)

router.register(
    "purchase-orders",
    PurchaseOrderViewSet,
    basename="purchase-order",
)


urlpatterns = [
    path("", include(router.urls)),
]