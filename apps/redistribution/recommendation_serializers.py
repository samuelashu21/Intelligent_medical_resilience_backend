from rest_framework import serializers

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
)


class RedistributionRecommendationSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    medicine_code = serializers.CharField(
        source="medicine.code",
        read_only=True,
    )

    donor_facility_name = serializers.CharField(
        source="donor_facility.name",
        read_only=True,
    )

    recipient_facility_name = serializers.CharField(
        source="recipient_facility.name",
        read_only=True,
    )

    class Meta:

        model = RedistributionRecommendation

        fields = [
            "id",
            "recommendation_number",
            "medicine",
            "medicine_name",
            "medicine_code",
            "donor_facility",
            "donor_facility_name",
            "recipient_facility",
            "recipient_facility_name",
            "donor_organization",
            "recipient_organization",
            "recommended_quantity",
            "unit_code",
            "donor_available_before",
            "recipient_available_before",
            "donor_available_after",
            "recipient_available_after",
            "donor_coverage_days_before",
            "recipient_coverage_days_before",
            "donor_coverage_days_after",
            "recipient_coverage_days_after",
            "priority",
            "status",
            "priority_score",
            "distance_km",
            "explanation",
            "algorithm_version",
            "generated_at",
            "expires_at",
            "reviewed_by",
            "reviewed_at",
            "review_reason",
            "created_at",
        ]

        read_only_fields = fields


class RecommendationReviewSerializer(serializers.Serializer):

    reason = serializers.CharField(
        required=True,
        min_length=5,
        max_length=2000,
    )


class GenerateRecommendationSerializer(serializers.Serializer):

    medicine = serializers.UUIDField()

    amc_months = serializers.IntegerField(
        min_value=1,
        max_value=12,
        default=3,
    )

    maximum_distance_km = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
