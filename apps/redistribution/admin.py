from django.contrib import admin

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
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