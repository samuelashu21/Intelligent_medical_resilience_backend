from django.urls import path

from apps.inventory.visibility_views import (
    FacilityStockVisibilityView,
    MedicineFacilityAvailabilityView,
    FacilityStockPortfolioView,
    FacilityStockClassificationView,
)


urlpatterns = [
    path(
        "facility-stock/",
        FacilityStockVisibilityView.as_view(),
        name="facility-stock-visibility",
    ),

    path(
        "medicine-availability/",
        MedicineFacilityAvailabilityView.as_view(),
        name="medicine-facility-availability",
    ),

    path(
        "facilities/<uuid:facility_id>/stock-portfolio/",
        FacilityStockPortfolioView.as_view(),
        name="facility-stock-portfolio",
    ),

    path(
        "classification/",
        FacilityStockClassificationView.as_view(),
        name="facility-stock-classification",
    ),
]