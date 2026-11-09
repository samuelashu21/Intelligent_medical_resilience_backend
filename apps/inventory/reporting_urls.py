from django.urls import path

from apps.inventory.reporting_views import (
    ExpiryReportView,
    FacilityStockSummaryView,
    HighCoverageReportView,
    LowStockReportView,
    StockDashboardView,
    StockoutReportView,
    StockStatusCSVExportView,
    StockStatusReportView,
)


urlpatterns = [
    path(
        "dashboard/",
        StockDashboardView.as_view(),
        name="stock-dashboard",
    ),
    path(
        "status/",
        StockStatusReportView.as_view(),
        name="stock-status-report",
    ),
    path(
        "stockouts/",
        StockoutReportView.as_view(),
        name="stockout-report",
    ),
    path(
        "low-stock/",
        LowStockReportView.as_view(),
        name="low-stock-report",
    ),
    path(
        "high-coverage/",
        HighCoverageReportView.as_view(),
        name="high-coverage-report",
    ),
    path(
        "expiry/",
        ExpiryReportView.as_view(),
        name="expiry-report",
    ),
    path(
        "facility-summary/",
        FacilityStockSummaryView.as_view(),
        name="facility-stock-summary",
    ),
    path(
        "export/csv/",
        StockStatusCSVExportView.as_view(),
        name="stock-status-csv-export",
    ),
]