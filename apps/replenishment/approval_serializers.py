from rest_framework import serializers

from apps.replenishment.models import (
    ApprovalDecision,
    ApprovalWorkflow,
    ApprovalWorkflowStage,
    ReplenishmentApproval,
)


class ApprovalWorkflowStageSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = ApprovalWorkflowStage
        fields = [
            "id",
            "sequence",
            "name",
            "organization_type_code",
            "required_role_code",
            "required_permission_code",
            "minimum_priority",
            "allow_revision",
            "allow_partial_approval",
            "is_final_stage",
        ]

        read_only_fields = ["id"]


class ApprovalWorkflowSerializer(
    serializers.ModelSerializer
):

    stages = ApprovalWorkflowStageSerializer(
        many=True,
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    class Meta:
        model = ApprovalWorkflow
        fields = [
            "id",
            "name",
            "organization",
            "organization_name",
            "description",
            "is_active",
            "stages",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ReplenishmentApprovalSerializer(
    serializers.ModelSerializer
):

    request_number = serializers.CharField(
        source="request.request_number",
        read_only=True,
    )

    stage_name = serializers.CharField(
        source="workflow_stage.name",
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    role_required = serializers.CharField(
        source="workflow_stage.required_role_code",
        read_only=True,
    )

    class Meta:
        model = ReplenishmentApproval
        fields = [
            "id",
            "request",
            "request_number",
            "workflow_stage",
            "stage_name",
            "organization",
            "organization_name",
            "role_required",
            "status",
            "assigned_at",
            "due_at",
            "completed_at",
            "decided_by",
            "escalation_level",
        ]

        read_only_fields = fields


class ApprovalDecisionSerializer(
    serializers.ModelSerializer
):

    decided_by_email = serializers.CharField(
        source="decided_by.email",
        read_only=True,
    )

    class Meta:
        model = ApprovalDecision
        fields = [
            "id",
            "approval",
            "decided_by",
            "decided_by_email",
            "decision",
            "comments",
            "approved_at",
            "metadata",
        ]

        read_only_fields = fields


class ApprovalActionSerializer(serializers.Serializer):

    decision = serializers.ChoiceField(
        choices=ApprovalDecision.Decision.choices,
    )

    comments = serializers.CharField(
        min_length=3,
    )