from rest_framework import serializers

from apps.redistribution.transfer_models import (
    TransferRequest,
    TransferRequestLine,
    TransferApprovalStage,
    TransferApprovalDecision,
)


class TransferLineSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    class Meta:
        model = TransferRequestLine

        fields = [
            "id",
            "optimization_allocation",
            "medicine",
            "medicine_name",
            "batch",
            "batch_number",
            "requested_quantity",
            "approved_quantity",
            "reserved_quantity",
            "unit_code",
            "notes",
        ]

        read_only_fields = [
            "id",
            "optimization_allocation",
            "approved_quantity",
            "reserved_quantity",
        ]


class TransferRequestSerializer(serializers.ModelSerializer):

    donor_name = serializers.CharField(
        source="donor_facility.name",
        read_only=True,
    )

    recipient_name = serializers.CharField(
        source="recipient_facility.name",
        read_only=True,
    )

    requested_by_email = serializers.CharField(
        source="requested_by.email",
        read_only=True,
    )

    lines = TransferLineSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = TransferRequest

        fields = [
            "id",
            "transfer_number",
            "source",
            "optimization_run",
            "donor_facility",
            "donor_name",
            "recipient_facility",
            "recipient_name",
            "organization",
            "requested_by",
            "requested_by_email",
            "priority",
            "status",
            "justification",
            "rejection_reason",
            "cancellation_reason",
            "current_approval_level",
            "submitted_at",
            "approved_at",
            "reserved_at",
            "created_at",
            "updated_at",
            "lines",
        ]

        read_only_fields = fields


class ManualTransferLineInputSerializer(
    serializers.Serializer
):
    medicine_id = serializers.UUIDField()
    batch_id = serializers.UUIDField()

    quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0.001,
    )

    unit_code = serializers.CharField(
        max_length=30,
    )


class ManualTransferCreateSerializer(
    serializers.Serializer
):
    donor_facility_id = serializers.UUIDField()
    recipient_facility_id = serializers.UUIDField()
    organization_id = serializers.UUIDField()

    justification = serializers.CharField(
        min_length=5,
    )

    priority = serializers.ChoiceField(
        choices=[
            "LOW",
            "NORMAL",
            "HIGH",
            "CRITICAL",
        ],
        default="NORMAL",
    )

    lines = ManualTransferLineInputSerializer(
        many=True,
        allow_empty=False,
    )


class TransferDecisionSerializer(serializers.Serializer):

    comments = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class TransferRejectSerializer(serializers.Serializer):

    reason = serializers.CharField(
        min_length=5,
    )


class TransferCancelSerializer(serializers.Serializer):

    reason = serializers.CharField(
        min_length=5,
    )


class TransferApprovalDecisionSerializer(
    serializers.ModelSerializer
):

    stage_name = serializers.CharField(
        source="stage.name",
        read_only=True,
    )

    approver_email = serializers.CharField(
        source="decided_by.email",
        read_only=True,
    )

    class Meta:
        model = TransferApprovalDecision

        fields = [
            "id",
            "stage",
            "stage_name",
            "decision",
            "decided_by",
            "approver_email",
            "comments",
            "decided_at",
        ]

        read_only_fields = fields


class TransferApprovalStageSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = TransferApprovalStage

        fields = [
            "id",
            "organization",
            "level",
            "name",
            "required_role_code",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]