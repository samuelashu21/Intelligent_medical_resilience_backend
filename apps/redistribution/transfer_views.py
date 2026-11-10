
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
)

from apps.redistribution.transfer_models import (
    TransferRequest,
    TransferApprovalStage,
)

from apps.redistribution.transfer_services import (
    create_manual_transfer,
    create_transfer_from_optimization,
    submit_transfer_for_approval,
    approve_transfer,
    reject_transfer,
    cancel_transfer,
)

from apps.redistribution.transfer_serializers import (
    TransferRequestSerializer,
    ManualTransferCreateSerializer,
    TransferDecisionSerializer,
    TransferRejectSerializer,
    TransferCancelSerializer,
    TransferApprovalStageSerializer,
)


class TransferRequestViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = TransferRequestSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_required_permission(self):

        if self.action in [
            "create_manual",
            "from_optimization",
        ]:
            return "redistribution.transfer.create"

        if self.action == "submit":
            return "redistribution.transfer.submit"

        if self.action in ["approve", "reject"]:
            return "redistribution.transfer.approve"

        if self.action == "cancel":
            return "redistribution.transfer.cancel"

        return "redistribution.transfer.view"

    def get_permissions(self):

        self.required_permissions = [
            self.get_required_permission()
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = (
            TransferRequest.objects
            .select_related(
                "donor_facility",
                "recipient_facility",
                "organization",
                "requested_by",
                "optimization_run",
            )
            .prefetch_related(
                "lines",
                "lines__medicine",
                "lines__batch",
                "approval_decisions",
            )
            .order_by("-created_at")
        )

        user = self.request.user

        if user.is_superuser:
            return queryset

        visible_ids = get_user_accessible_facility_ids(
            user,
            permission_code="redistribution.transfer.view",
        )

        return queryset.filter(
            Q(donor_facility_id__in=visible_ids)
            & Q(recipient_facility_id__in=visible_ids)
        ).distinct()

    @action(
        detail=False,
        methods=["post"],
        url_path="manual",
    )
    def create_manual(self, request):

        serializer = ManualTransferCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        values = serializer.validated_data

        try:
            transfer = create_manual_transfer(
                donor_facility_id=values["donor_facility_id"],
                recipient_facility_id=values[
                    "recipient_facility_id"
                ],
                organization_id=values["organization_id"],
                lines=values["lines"],
                user=request.user,
                justification=values["justification"],
                priority=values["priority"],
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            TransferRequestSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="from-optimization",
    )
    def from_optimization(self, request):

        optimization_run_id = request.data.get(
            "optimization_run_id"
        )

        justification = request.data.get(
            "justification"
        )

        priority = request.data.get(
            "priority",
            "NORMAL",
        )

        if not optimization_run_id:
            raise ValidationError(
                "optimization_run_id is required."
            )

        if (
            not justification
            or len(justification.strip()) < 5
        ):
            raise ValidationError(
                "A meaningful justification is required."
            )

        try:
            transfers = create_transfer_from_optimization(
                optimization_run_id=optimization_run_id,
                user=request.user,
                justification=justification,
                priority=priority,
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            TransferRequestSerializer(
                transfers,
                many=True,
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(self, request, pk=None):

        transfer = self.get_object()

        try:
            transfer = submit_transfer_for_approval(
                transfer_id=transfer.pk,
                user=request.user,
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            TransferRequestSerializer(transfer).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):

        serializer = TransferDecisionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        transfer = self.get_object()

        try:
            transfer = approve_transfer(
                transfer_id=transfer.pk,
                user=request.user,
                comments=serializer.validated_data.get(
                    "comments",
                    "",
                ),
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            TransferRequestSerializer(transfer).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    def reject(self, request, pk=None):

        serializer = TransferRejectSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        transfer = self.get_object()

        try:
            transfer = reject_transfer(
                transfer_id=transfer.pk,
                user=request.user,
                reason=serializer.validated_data["reason"],
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            TransferRequestSerializer(transfer).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):

        serializer = TransferCancelSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        transfer = self.get_object()

        try:
            transfer = cancel_transfer(
                transfer_id=transfer.pk,
                user=request.user,
                reason=serializer.validated_data["reason"],
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            TransferRequestSerializer(transfer).data
        )


class TransferApprovalStageViewSet(viewsets.ModelViewSet):

    serializer_class = TransferApprovalStageSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_permissions(self):

        self.required_permissions = [
            (
                "redistribution.transfer.policy.manage"
                if self.action in [
                    "create",
                    "update",
                    "partial_update",
                    "destroy",
                ]
                else "redistribution.transfer.view"
            )
        ]

        return super().get_permissions()

    def get_queryset(self):

        return TransferApprovalStage.objects.filter(
            is_active=True
        ).select_related(
            "organization"
        ).order_by(
            "organization_id",
            "level",
        )

    def perform_destroy(self, instance):

        # Preserve historical approval policy records.
        instance.is_active = False

        instance.save(
            update_fields=["is_active"]
        )
