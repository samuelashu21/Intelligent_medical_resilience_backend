from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission

from apps.inventory.models import StockPolicy
from apps.inventory.permissions import HasInventoryPermission

from apps.inventory.stock_policy_serializers import (
    StockPolicySerializer,
)

from apps.inventory.stock_policy_services import (
    activate_stock_policy,
    deactivate_stock_policy,
    evaluate_stock_policy,
)


class StockPolicyViewSet(viewsets.ModelViewSet):

    serializer_class = StockPolicySerializer
    permission_classes = [HasInventoryPermission]

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def get_required_permission(self):
        if self.action == "create":
            return "inventory.policy.create"

        if self.action in ["update", "partial_update"]:
            return "inventory.policy.update"

        if self.action in [
            "activate",
            "deactivate",
        ]:
            return "inventory.policy.manage"

        return "inventory.policy.view"

    def get_permissions(self):
        self.required_permissions = [self.get_required_permission()]

        return super().get_permissions()

    def get_queryset(self):
        queryset = StockPolicy.objects.select_related(
            "organization",
            "facility",
            "medicine",
            "created_by",
            "updated_by",
        )

        user = self.request.user

        if user.is_superuser:
            return queryset.order_by(
                "organization__name",
                "medicine__generic_name",
            )

        organization_ids = get_user_accessible_organization_ids(
            user,
            permission_code="inventory.policy.view",
        )

        return queryset.filter(organization_id__in=organization_ids).order_by(
            "organization__name",
            "medicine__generic_name",
        )

    def perform_create(self, serializer):
        user = self.request.user
        organization = serializer.validated_data["organization"]
        facility = serializer.validated_data.get("facility")

        if not user.is_superuser:
            if not user_has_permission(
                user,
                "inventory.policy.create",
                organization=organization,
            ):
                raise PermissionDenied(
                    "You cannot create policies for this organization."
                )

            if facility and not user_has_permission(
                user,
                "inventory.policy.create",
                facility=facility,
            ):
                raise PermissionDenied("You cannot create policies for this facility.")

        serializer.save(
            created_by=user,
            updated_by=user,
            status=StockPolicy.PolicyStatus.DRAFT,
        )

    def perform_update(self, serializer):
        user = self.request.user
        organization = serializer.instance.organization

        if not user.is_superuser and not user_has_permission(
            user,
            "inventory.policy.update",
            organization=organization,
        ):
            raise PermissionDenied("You cannot update policies for this organization.")

        serializer.save(updated_by=user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        policy = self.get_object()

        if not request.user.is_superuser and not user_has_permission(
            request.user,
            "inventory.policy.manage",
            organization=policy.organization,
        ):
            raise PermissionDenied("You cannot activate this stock policy.")

        policy = activate_stock_policy(
            policy_id=policy.pk,
            user=request.user,
        )

        return Response(
            self.get_serializer(policy).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        policy = self.get_object()

        if not request.user.is_superuser and not user_has_permission(
            request.user,
            "inventory.policy.manage",
            organization=policy.organization,
        ):
            raise PermissionDenied("You cannot deactivate this stock policy.")

        policy = deactivate_stock_policy(
            policy_id=policy.pk,
            user=request.user,
        )

        return Response(
            self.get_serializer(policy).data,
            status=status.HTTP_200_OK,
        )


class StockPolicyEvaluationView(APIView):

    permission_classes = [HasInventoryPermission]

    required_permissions = ["inventory.policy.view"]

    def get(self, request):
        facility_id = request.query_params.get("facility")
        medicine_id = request.query_params.get("medicine")

        if not facility_id or not medicine_id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {
                    "facility": "Facility ID is required.",
                    "medicine": "Medicine ID is required.",
                }
            )

        from apps.facilities.models import Facility
        from apps.medicines.models import Medicine

        facility = (
            Facility.objects.filter(pk=facility_id)
            .select_related("organization")
            .first()
        )

        if not facility:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"facility": "Facility not found."})

        if not Medicine.objects.filter(pk=medicine_id).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"medicine": "Medicine not found."})

        if not request.user.is_superuser:
            if not user_has_permission(
                request.user,
                "inventory.policy.view",
                facility=facility,
            ):
                raise PermissionDenied(
                    "You cannot evaluate stock policies for this facility."
                )

        result = evaluate_stock_policy(
            facility_id=facility.pk,
            medicine_id=medicine_id,
        )

        return Response(result)
