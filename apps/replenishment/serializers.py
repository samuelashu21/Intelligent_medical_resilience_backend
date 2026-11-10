from rest_framework import serializers

from apps.replenishment.models import (
    ReplenishmentRequest,
    ReplenishmentRequestLine,
)


class ReplenishmentRequestLineSerializer(
    serializers.ModelSerializer
):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    medicine_code = serializers.CharField(
        source="medicine.code",
        read_only=True,
    )

    supplier_name = serializers.CharField(
        source="preferred_supplier.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ReplenishmentRequestLine

        fields = [
            "id",
            "medicine",
            "medicine_name",
            "medicine_code",
            "preferred_supplier",
            "supplier_name",
            "requested_quantity",
            "recommended_quantity",
            "approved_quantity",
            "unit_code",
            "reason",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "recommended_quantity",
            "approved_quantity",
            "created_at",
            "updated_at",
        ]


class ReplenishmentRequestSerializer(
    serializers.ModelSerializer
):

    items = ReplenishmentRequestLineSerializer(
        many=True,
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    requester_email = serializers.CharField(
        source="requested_by.email",
        read_only=True,
    )

    approved_by_email = serializers.CharField(
        source="approved_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ReplenishmentRequest

        fields = [
            "id",
            "request_number",
            "facility",
            "facility_name",
            "organization",
            "requested_by",
            "requester_email",
            "priority",
            "source",
            "status",
            "justification",
            "requested_at",
            "submitted_at",
            "approved_by",
            "approved_by_email",
            "approved_at",
            "rejected_by",
            "rejected_at",
            "rejection_reason",
            "cancelled_by",
            "cancelled_at",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class ReplenishmentRequestCreateSerializer(
    serializers.Serializer
):

    facility = serializers.UUIDField()

    priority = serializers.ChoiceField(
        choices=ReplenishmentRequest.Priority.choices,
        default=ReplenishmentRequest.Priority.NORMAL,
    )

    justification = serializers.CharField(
        min_length=5,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    items = ReplenishmentRequestLineSerializer(
        many=True,
        allow_empty=False,
    )

    def validate_items(self, items):
        medicine_ids = [
            str(item["medicine"].pk)
            for item in items
        ]

        if len(medicine_ids) != len(set(medicine_ids)):
            raise serializers.ValidationError(
                "A medicine can only appear once in a request."
            )

        for item in items:
            if item["requested_quantity"] <= 0:
                raise serializers.ValidationError(
                    "Every requested quantity must be positive."
                )

        return items


class PolicyRequestCreateSerializer(serializers.Serializer):

    facility = serializers.UUIDField()

    medicines = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )

    priority = serializers.ChoiceField(
        choices=ReplenishmentRequest.Priority.choices,
        default=ReplenishmentRequest.Priority.NORMAL,
    )

    justification = serializers.CharField(
        min_length=5,
    )

    def validate_medicines(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate medicines are not allowed."
            )

        return value


class ReplenishmentApprovalSerializer(serializers.Serializer):

    approved_quantities = serializers.DictField(
        child=serializers.DecimalField(
            max_digits=18,
            decimal_places=3,
            min_value=0,
        ),
        required=False,
    )


class ReplenishmentRejectionSerializer(serializers.Serializer):

    reason = serializers.CharField(
        min_length=5,
    )


class ReplenishmentCancellationSerializer(serializers.Serializer):

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )