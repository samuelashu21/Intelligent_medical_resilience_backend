from rest_framework import serializers

from apps.inventory.models import (
    StockCount,
    StockCountLine,
    StockReconciliation,
)


class StockCountLineSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    medicine_name = serializers.CharField(
        source="batch.medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = StockCountLine
        fields = [
            "id",
            "stock_count",
            "batch",
            "batch_number",
            "medicine_name",
            "system_quantity",
            "physical_quantity",
            "variance",
            "reason",
            "explanation",
            "counted_by",
            "counted_at",
            "is_reviewed",
        ]

        read_only_fields = [
            "id",
            "stock_count",
            "batch",
            "batch_number",
            "medicine_name",
            "system_quantity",
            "variance",
            "counted_by",
            "counted_at",
            "is_reviewed",
        ]


class StockCountSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    line_count = serializers.IntegerField(
        source="lines.count",
        read_only=True,
    )

    class Meta:
        model = StockCount
        fields = [
            "id",
            "reference_number",
            "warehouse",
            "warehouse_name",
            "count_method",
            "status",
            "scheduled_date",
            "started_at",
            "submitted_at",
            "approved_at",
            "posted_at",
            "created_by",
            "submitted_by",
            "approved_by",
            "notes",
            "line_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "started_at",
            "submitted_at",
            "approved_at",
            "posted_at",
            "created_by",
            "submitted_by",
            "approved_by",
            "created_at",
            "updated_at",
        ]


class StockReconciliationSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(
        source="count_line.batch.batch_number",
        read_only=True,
    )

    class Meta:
        model = StockReconciliation
        fields = [
            "id",
            "stock_count",
            "count_line",
            "batch_number",
            "system_quantity",
            "physical_quantity",
            "variance",
            "adjustment_movement",
            "reason",
            "explanation",
            "posted_by",
            "posted_at",
            "created_at",
        ]

        read_only_fields = fields


class RecordPhysicalCountSerializer(serializers.Serializer):
    physical_quantity = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        min_value=0,
    )

    reason = serializers.ChoiceField(
        choices=__import__(
            "apps.inventory.models",
            fromlist=["StockVarianceReason"],
        ).StockVarianceReason.choices,
        required=False,
        allow_blank=True,
    )

    explanation = serializers.CharField(
        required=False,
        allow_blank=True,
    )
