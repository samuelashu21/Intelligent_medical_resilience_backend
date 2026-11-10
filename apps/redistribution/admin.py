from django.contrib import admin

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
)

from django.contrib import admin

from apps.redistribution.optimization_models import (
    RedistributionTransportProfile,
    RedistributionOptimizationRun,
    RedistributionOptimizationAllocation,
)


@admin.register(RedistributionRecommendation)
class RedistributionRecommendationAdmin(admin.ModelAdmin):

    list_display = [
        "recommendation_number",
        "medicine",
        "donor_facility",
        "recipient_facility",
        "recommended_quantity",
        "priority",
        "priority_score",
        "status",
        "generated_at",
    ]

    list_filter = [
        "status",
        "priority",
        "generated_at",
        "algorithm_version",
    ]

    search_fields = [
        "recommendation_number",
        "medicine__generic_name",
        "donor_facility__name",
        "recipient_facility__name",
    ]

    readonly_fields = [
        "id",
        "recommendation_number",
        "medicine",
        "donor_facility",
        "recipient_facility",
        "recommended_quantity",
        "unit_code",
        "priority_score",
        "distance_km",
        "explanation",
        "algorithm_version",
        "generated_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



@admin.register(RedistributionTransportProfile)
class RedistributionTransportProfileAdmin(admin.ModelAdmin):

    list_display = [
        "medicine",
        "inventory_unit_code",
        "capacity_units_per_inventory_unit",
        "is_active",
        "effective_from",
        "effective_until",
    ]

    list_filter = [
        "is_active",
        "effective_from",
    ]

    search_fields = [
        "medicine__generic_name",
        "medicine__code",
        "inventory_unit_code",
    ]


@admin.register(RedistributionOptimizationRun)
class RedistributionOptimizationRunAdmin(admin.ModelAdmin):

    list_display = [
        "run_number",
        "status",
        "solver_status",
        "generated_by",
        "total_distance_km",
        "total_unmet_shortage_units",
        "created_at",
    ]

    list_filter = [
        "status",
        "solver_status",
        "algorithm_version",
        "created_at",
    ]

    search_fields = [
        "run_number",
        "generated_by__email",
    ]

    readonly_fields = [
        field.name
        for field in RedistributionOptimizationRun._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RedistributionOptimizationAllocation)
class RedistributionOptimizationAllocationAdmin(admin.ModelAdmin):

    list_display = [
        "optimization_run",
        "medicine",
        "donor_facility",
        "recipient_facility",
        "batch",
        "quantity",
        "distance_km",
        "status",
    ]

    list_filter = [
        "status",
        "medicine",
    ]

    search_fields = [
        "optimization_run__run_number",
        "medicine__generic_name",
        "donor_facility__name",
        "recipient_facility__name",
        "batch__batch_number",
    ]

    readonly_fields = [
        field.name
        for field in RedistributionOptimizationAllocation._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False