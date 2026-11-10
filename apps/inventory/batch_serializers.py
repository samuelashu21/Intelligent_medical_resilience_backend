from rest_framework import serializers

from apps.inventory.models import (
    BatchExpiryAlert,
    BatchLifecycleEvent,
)


class BatchLifecycleEventSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.EmailField(
        source="performed_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = BatchLifecycleEvent
        fields = [
            "id",
            "batch",
            "action",
            "previous_status",
            "new_status",
            "reason",
            "reference_number",
            "performed_by",
            "performed_by_email",
            "performed_by_label",
            "metadata",
            "occurred_at",
        ]

        read_only_fields = fields


class BatchExpiryAlertSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    medicine_name = serializers.CharField(
        source="batch.medicine.generic_name",
        read_only=True,
    )

    warehouse_name = serializers.CharField(
        source="batch.warehouse.name",
        read_only=True,
    )

    class Meta:
        model = BatchExpiryAlert
        fields = [
            "id",
            "batch",
            "batch_number",
            "medicine_name",
            "warehouse_name",
            "alert_level",
            "threshold_days",
            "message",
            "is_active",
            "first_detected_at",
            "last_detected_at",
            "resolved_at",
        ]

        read_only_fields = fields
