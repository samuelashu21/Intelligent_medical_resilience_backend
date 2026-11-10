from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.consumption.views import (
    ConsumptionAnomalyViewSet,
    DailyConsumptionViewSet,
    MonthlyConsumptionReportViewSet,
)

from apps.consumption.analytics_views import (
    AverageMonthlyConsumptionView,
    DetectConsumptionAnomaliesView,
)

router = DefaultRouter()

router.register(
    "daily",
    DailyConsumptionViewSet,
    basename="daily-consumption",
)

router.register(
    "monthly-reports",
    MonthlyConsumptionReportViewSet,
    basename="monthly-consumption-report",
)

router.register(
    "anomalies",
    ConsumptionAnomalyViewSet,
    basename="consumption-anomaly",
)


urlpatterns = [
    path(
        "analytics/amc/",
        AverageMonthlyConsumptionView.as_view(),
        name="consumption-amc",
    ),
    path(
        "analytics/detect-anomalies/",
        DetectConsumptionAnomaliesView.as_view(),
        name="detect-consumption-anomalies",
    ),
    path("", include(router.urls)),
]
