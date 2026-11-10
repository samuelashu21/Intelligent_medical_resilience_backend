from rest_framework import serializers

from apps.logistics.receiving_models import (
    ReceivingRecord,
    ReceivingLine,
    ReceivingDiscrepancy,
)


class ReceivingLineSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    missing_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        read_only=True,
    )

    excess_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        read_only=True,
    )

    rejected_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        read_only=True,
    )

    class Meta:
        model = ReceivingLine

        fields = [
            "id",
            "shipment_line",
            "medicine",
            "medicine_name",
            "batch",
            "batch_number",
            "dispatched_quantity",
            "physically_received_quantity",
            "accepted_quantity",
            "damaged_quantity",
            "expired_quantity",
            "other_rejected_quantity",
            "missing_quantity",
            "excess_quantity",
            "rejected_quantity",
            "unit_code",
            "inspection_notes",
        ]

        read_only_fields = [
            "id",
            "shipment_line",
            "medicine",
            "batch",
            "dispatched_quantity",
            "unit_code",
        ]


class ReceivingRecordSerializer(serializers.ModelSerializer):

    lines = ReceivingLineSerializer(
        many=True,
        read_only=True,
    )

    shipment_number = serializers.CharField(
        source="shipment.shipment_number",
        read_only=True,
    )

    class Meta:
        model = ReceivingRecord

        fields = [
            "id",
            "receipt_number",
            "shipment",
            "shipment_number",
            "recipient_facility",
            "receiving_warehouse",
            "status",
            "received_by",
            "submitted_by",
            "approved_by",
            "posted_by",
            "received_at",
            "submitted_at",
            "approved_at",
            "posted_at",
            "rejection_reason",
            "notes",
            "created_at",
            "updated_at",
            "lines",
        ]

        read_only_fields = fields


class ReceivingRecordCreateSerializer(serializers.Serializer):

    shipment_id = serializers.UUIDField()

    receiving_warehouse_id = serializers.UUIDField()

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class ReceivingLineUpdateSerializer(serializers.Serializer):

    physically_received_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0,
    )

    accepted_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0,
    )

    damaged_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0,
        required=False,
        default=0,
    )

    expired_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0,
        required=False,
        default=0,
    )

    other_rejected_quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0,
        required=False,
        default=0,
    )

    inspection_notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class ReceivingRejectSerializer(serializers.Serializer):

    reason = serializers.CharField(min_length=5)


class DiscrepancyResolveSerializer(serializers.Serializer):

    decision = serializers.ChoiceField(
        choices=["ACCEPTED", "REJECTED"],
    )

    resolution_notes = serializers.CharField(
        min_length=5,
    )


class ReceivingDiscrepancySerializer(serializers.ModelSerializer):

    class Meta:
        model = ReceivingDiscrepancy

        fields = [
            "id",
            "receiving_line",
            "discrepancy_type",
            "quantity",
            "status",
            "description",
            "resolution_notes",
            "reported_by",
            "resolved_by",
            "reported_at",
            "resolved_at",
        ]

        read_only_fields = fields