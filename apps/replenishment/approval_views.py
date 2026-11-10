from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission
from apps.accounts.permissions import HasSystemPermission

from apps.replenishment.models import (
    ApprovalWorkflow,
    ApprovalDecision,
    ReplenishmentApproval,
)

from apps.replenishment.approval_services import (
    decide_approval_stage,
)

from apps.replenishment.approval_serializers import (
    ApprovalActionSerializer,
    ApprovalDecisionSerializer,
    ApprovalWorkflowSerializer,
    ReplenishmentApprovalSerializer,
)


class ApprovalWorkflowViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ApprovalWorkflowSerializer
    permission_classes = [HasSystemPermission]

    def get_permissions(self):
        self.required_permissions = ["replenishment.workflow.view"]
        return super().get_permissions()

    def get_queryset(self):
        queryset = ApprovalWorkflow.objects.select_related(
            "organization",
            "created_by",
        ).prefetch_related("stages")

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="replenishment.workflow.view",
        )

        return queryset.filter(organization_id__in=organization_ids)


class ReplenishmentApprovalViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ReplenishmentApprovalSerializer
    permission_classes = [HasSystemPermission]

    def get_permissions(self):
        if self.action == "decide":
            self.required_permissions = ["replenishment.approve"]
        else:
            self.required_permissions = ["replenishment.approval.view"]

        return super().get_permissions()

    def get_queryset(self):
        queryset = ReplenishmentApproval.objects.select_related(
            "request",
            "workflow_stage",
            "organization",
            "decided_by",
        )

        user = self.request.user

        if user.is_superuser:
            return queryset.order_by("workflow_stage__sequence")

        organization_ids = get_user_accessible_organization_ids(
            user,
            permission_code="replenishment.approval.view",
        )

        return queryset.filter(organization_id__in=organization_ids).order_by(
            "workflow_stage__sequence"
        )

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        approval = self.get_object()

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = decide_approval_stage(
                approval_id=approval.pk,
                user=request.user,
                decision=serializer.validated_data["decision"],
                comments=serializer.validated_data["comments"],
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            ReplenishmentApprovalSerializer(result).data,
            status=status.HTTP_200_OK,
        )


class ApprovalDecisionViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ApprovalDecisionSerializer
    permission_classes = [HasSystemPermission]

    def get_permissions(self):
        self.required_permissions = ["replenishment.approval.view"]

        return super().get_permissions()

    def get_queryset(self):
        queryset = ApprovalDecision.objects.select_related(
            "approval",
            "approval__request",
            "decided_by",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="replenishment.approval.view",
        )

        return queryset.filter(approval__organization_id__in=organization_ids)
