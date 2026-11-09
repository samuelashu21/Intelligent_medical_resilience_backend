from rest_framework import serializers

from apps.consumption.models import (
    ConsumptionAnomaly,
    DailyConsumption,
    MonthlyConsumptionReport,
)


class DailyConsumptionSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = DailyConsumption
        fields = [
            "id",
            "facility",
            "facility_name",
            "medicine",
            "medicine_name",
            "batch",
            "batch_number",
            "consumption_date",
            "quantity",
            "unit_code",
            "source",
            "reporting_method",
            "reference_number",
            "notes",
            "recorded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "recorded_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        batch = attrs.get("batch")
        medicine = attrs.get("medicine")
        facility = attrs.get("facility")

        if batch and medicine and batch.medicine_id != medicine.pk:
            raise serializers.ValidationError(
                {"batch": "Batch does not belong to the selected medicine."}
            )

        if batch and facility:
            if (
                batch.warehouse.organization_id
                != facility.organization_id
            ):
                raise serializers.ValidationError(
                    {"batch": "Batch is outside the facility organization."}
                )

        return attrs


class MonthlyConsumptionReportSerializer(
    serializers.ModelSerializer
):
    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = MonthlyConsumptionReport
        fields = [
            "id",
            "facility",
            "facility_name",
            "medicine",
            "medicine_name",
            "year",
            "month",
            "opening_balance",
            "received_quantity",
            "consumed_quantity",
            "losses_quantity",
            "closing_balance",
            "stockout_days",
            "reporting_unit",
            "status",
            "submitted_by",
            "approved_by",
            "submitted_at",
            "approved_at",
            "rejection_reason",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "consumed_quantity",
            "status",
            "submitted_by",
            "approved_by",
            "submitted_at",
            "approved_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class ConsumptionAnomalySerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = ConsumptionAnomaly
        fields = [
            "id",
            "facility",
            "facility_name",
            "medicine",
            "medicine_name",
            "anomaly_type",
            "reporting_period_start",
            "reporting_period_end",
            "observed_quantity",
            "expected_quantity",
            "description",
            "is_resolved",
            "resolution_notes",
            "detected_at",
            "resolved_at",
        ]

        read_only_fields = fields