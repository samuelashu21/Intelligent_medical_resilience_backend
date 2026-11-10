from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission

from apps.accounts.permissions import HasSystemPermission

from apps.facilities.models import Facility

from apps.replenishment.models import ReplenishmentRequest

from apps.replenishment.serializers import (
    PolicyRequestCreateSerializer,
    ReplenishmentApprovalSerializer,
    ReplenishmentCancellationSerializer,
    ReplenishmentRejectionSerializer,
    ReplenishmentRequestCreateSerializer,
    ReplenishmentRequestSerializer,
)

from apps.replenishment.services import (
    approve_replenishment_request,
    cancel_replenishment_request,
    create_replenishment_request,
    generate_policy_replenishment_request,
    reject_replenishment_request,
    submit_replenishment_request,
)


class ReplenishmentRequestViewSet(viewsets.ModelViewSet):

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    serializer_class = ReplenishmentRequestSerializer
    permission_classes = [HasSystemPermission]

    def get_required_permission(self):
        if self.action == "create":
            return "replenishment.create"

        if self.action == "submit":
            return "replenishment.submit"

        if self.action == "approve":
            return "replenishment.approve"

        if self.action == "reject":
            return "replenishment.approve"

        if self.action == "cancel":
            return "replenishment.cancel"

        return "replenishment.view"

    def get_permissions(self):
        self.required_permissions = [
            self.get_required_permission()
        ]

        return super().get_permissions()

    def get_queryset(self):
        queryset = ReplenishmentRequest.objects.select_related(
            "facility",
            "organization",
            "requested_by",
            "approved_by",
            "rejected_by",
            "cancelled_by",
        ).prefetch_related(
            "items",
            "items__medicine",
            "items__preferred_supplier",
        )

        user = self.request.user

        if user.is_superuser:
            return queryset.order_by("-requested_at")

        organization_ids = get_user_accessible_organization_ids(
            user,
            permission_code="replenishment.view",
        )

        return queryset.filter(
            organization_id__in=organization_ids
        ).order_by("-requested_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ReplenishmentRequestCreateSerializer

        return ReplenishmentRequestSerializer

    def perform_create(self, serializer):
        facility_id = serializer.validated_data["facility"]

        facility = Facility.objects.filter(
            pk=facility_id,
            is_active=True,
        ).select_related("organization").first()

        if not facility:
            raise ValidationError({
                "facility": "Active facility not found."
            })

        if not self.request.user.is_superuser:
            if not user_has_permission(
                self.request.user,
                "replenishment.create",
                facility=facility,
            ):
                raise PermissionDenied(
                    "You cannot create replenishment requests "
                    "for this facility."
                )

        items = []

        for item in serializer.validated_data["items"]:
            items.append({
                "medicine_id": item["medicine"].pk,
                "requested_quantity": item["requested_quantity"],
                "unit_code": item["unit_code"],
                "preferred_supplier_id": (
                    item["preferred_supplier"].pk
                    if item.get("preferred_supplier")
                    else None
                ),
                "reason": item.get("reason", ""),
            })

        request = create_replenishment_request(
            facility_id=facility.pk,
            requested_by=self.request.user,
            justification=serializer.validated_data["justification"],
            items=items,
            priority=serializer.validated_data["priority"],
            source=ReplenishmentRequest.Source.MANUAL,
            notes=serializer.validated_data.get("notes", ""),
        )

        self.created_request = request

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        output = ReplenishmentRequestSerializer(
            self.created_request,
            context=self.get_serializer_context(),
        )

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        replenishment_request = self.get_object()

        if (
            not request.user.is_superuser
            and not user_has_permission(
                request.user,
                "replenishment.submit",
                facility=replenishment_request.facility,
            )
        ):
            raise PermissionDenied(
                "You cannot submit this request."
            )

        try:
            result = submit_replenishment_request(
                replenishment_request.pk,
                request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(result).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        replenishment_request = self.get_object()

        if (
            not request.user.is_superuser
            and not user_has_permission(
                request.user,
                "replenishment.approve",
                facility=replenishment_request.facility,
            )
        ):
            raise PermissionDenied(
                "You cannot approve this request."
            )

        serializer = ReplenishmentApprovalSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = approve_replenishment_request(
                replenishment_request.pk,
                request.user,
                serializer.validated_data.get(
                    "approved_quantities"
                ),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(result).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        replenishment_request = self.get_object()

        if (
            not request.user.is_superuser
            and not user_has_permission(
                request.user,
                "replenishment.approve",
                facility=replenishment_request.facility,
            )
        ):
            raise PermissionDenied(
                "You cannot reject this request."
            )

        serializer = ReplenishmentRejectionSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = reject_replenishment_request(
                replenishment_request.pk,
                request.user,
                serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(result).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        replenishment_request = self.get_object()

        if (
            not request.user.is_superuser
            and not user_has_permission(
                request.user,
                "replenishment.cancel",
                facility=replenishment_request.facility,
            )
        ):
            raise PermissionDenied(
                "You cannot cancel this request."
            )

        serializer = ReplenishmentCancellationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = cancel_replenishment_request(
                replenishment_request.pk,
                request.user,
                serializer.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(result).data
        )


class PolicyReplenishmentRequestView(APIView):

    permission_classes = [HasSystemPermission]

    required_permissions = ["replenishment.create"]

    def post(self, request):
        serializer = PolicyRequestCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        facility = Facility.objects.filter(
            pk=serializer.validated_data["facility"],
            is_active=True,
        ).select_related("organization").first()

        if not facility:
            raise ValidationError({
                "facility": "Active facility not found."
            })

        if (
            not request.user.is_superuser
            and not user_has_permission(
                request.user,
                "replenishment.create",
                facility=facility,
            )
        ):
            raise PermissionDenied(
                "You cannot create replenishment requests "
                "for this facility."
            )

        try:
            result = generate_policy_replenishment_request(
                facility_id=facility.pk,
                medicine_ids=serializer.validated_data["medicines"],
                requested_by=request.user,
                justification=serializer.validated_data["justification"],
                priority=serializer.validated_data["priority"],
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            ReplenishmentRequestSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )