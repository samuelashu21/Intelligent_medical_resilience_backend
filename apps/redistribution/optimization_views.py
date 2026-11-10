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

from apps.redistribution.optimization_models import (
    RedistributionOptimizationRun,
    RedistributionTransportProfile,
)

from apps.redistribution.optimization_services import (
    run_redistribution_optimization,
)

from apps.redistribution.optimization_serializers import (
    OptimizationRequestSerializer,
    OptimizationRunSerializer,
    TransportProfileSerializer,
)


class RedistributionOptimizationViewSet(viewsets.ReadOnlyModelViewSet):

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    serializer_class = OptimizationRunSerializer

    def get_required_permission(self):

        if self.action == "optimize":
            return "redistribution.optimization.run"

        return "redistribution.optimization.view"

    def get_permissions(self):

        self.required_permissions = [self.get_required_permission()]

        return super().get_permissions()

    def get_queryset(self):

        queryset = RedistributionOptimizationRun.objects.prefetch_related(
            "allocations",
            "allocations__medicine",
            "allocations__donor_facility",
            "allocations__recipient_facility",
            "allocations__batch",
        ).order_by("-created_at")

        user = self.request.user

        if user.is_superuser:
            return queryset

        visible_ids = get_user_accessible_facility_ids(
            user,
            permission_code="redistribution.optimization.view",
        )

        return queryset.filter(
            Q(generated_by=user)
            | Q(
                allocations__donor_facility_id__in=visible_ids,
                allocations__recipient_facility_id__in=visible_ids,
            )
        ).distinct()

    @action(
        detail=False,
        methods=["post"],
        url_path="run",
    )
    def optimize(self, request):

        serializer = OptimizationRequestSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        values = serializer.validated_data

        try:

            run = run_redistribution_optimization(
                user=request.user,
                medicine_ids=values.get("medicines"),
                amc_months=values["amc_months"],
                maximum_distance_km=values.get("maximum_distance_km"),
                vehicle_capacity_units=values["vehicle_capacity_units"],
                max_active_routes=values.get("max_active_routes"),
                max_solver_seconds=values["max_solver_seconds"],
            )

        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc))

        return Response(
            OptimizationRunSerializer(run).data,
            status=(
                status.HTTP_201_CREATED
                if run.status == "COMPLETED"
                else status.HTTP_200_OK
            ),
        )


class RedistributionTransportProfileViewSet(viewsets.ModelViewSet):

    serializer_class = TransportProfileSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_required_permission(self):

        if self.action in ["create", "update", "partial_update"]:
            return "redistribution.transport_profile.manage"

        return "redistribution.optimization.view"

    def get_permissions(self):

        self.required_permissions = [self.get_required_permission()]

        return super().get_permissions()

    def get_queryset(self):

        return RedistributionTransportProfile.objects.select_related(
            "medicine"
        ).order_by("medicine__generic_name")

    def perform_create(self, serializer):

        serializer.save(created_by=self.request.user)
