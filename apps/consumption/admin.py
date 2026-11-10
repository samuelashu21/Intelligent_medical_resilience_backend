from django.contrib import admin

from apps.consumption.models import (
    ConsumptionAnomaly,
    DailyConsumption,
    MonthlyConsumptionReport,
)


@admin.register(DailyConsumption)
class DailyConsumptionAdmin(admin.ModelAdmin):
    list_display = (
        "facility",
        "medicine",
        "consumption_date",
        "quantity",
        "unit_code",
        "source",
        "recorded_by",
    )

    list_filter = (
        "source",
        "reporting_method",
        "consumption_date",
    )

    search_fields = (
        "facility__name",
        "medicine__generic_name",
        "medicine__code",
        "reference_number",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "consumption_date"


@admin.register(MonthlyConsumptionReport)
class MonthlyConsumptionReportAdmin(admin.ModelAdmin):
    list_display = (
        "facility",
        "medicine",
        "year",
        "month",
        "consumed_quantity",
        "stockout_days",
        "status",
    )

    list_filter = (
        "status",
        "year",
        "month",
    )

    search_fields = (
        "facility__name",
        "medicine__generic_name",
    )

    readonly_fields = (
        "id",
        "submitted_at",
        "approved_at",
        "created_at",
        "updated_at",
    )


@admin.register(ConsumptionAnomaly)
class ConsumptionAnomalyAdmin(admin.ModelAdmin):
    list_display = (
        "facility",
        "medicine",
        "anomaly_type",
        "is_resolved",
        "detected_at",
    )

    list_filter = (
        "anomaly_type",
        "is_resolved",
        "detected_at",
    )

    search_fields = (
        "facility__name",
        "medicine__generic_name",
        "description",
    )

    readonly_fields = (
        "id",
        "detected_at",
    )
