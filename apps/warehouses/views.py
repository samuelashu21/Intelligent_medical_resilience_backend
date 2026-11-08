from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)

from apps.warehouses.models import (
    StorageLocation,
    StorageZone,
    Warehouse,
    WarehouseCapacitySnapshot,
    WarehouseManagerAssignment,
    WarehouseStatus,
    WarehouseTemperatureReading,
)

from apps.warehouses.permissions import HasWarehousePermission

from apps.warehouses.serializers import (
    StorageLocationSerializer,
    StorageZoneSerializer,
    WarehouseCapacitySnapshotSerializer,
    WarehouseManagerAssignmentSerializer,
    WarehouseSerializer,
    WarehouseTemperatureReadingSerializer,
)

from apps.warehouses.services import (
    activate_warehouse,
    assign_warehouse_manager,
    close_warehouse,
    get_warehouse_capacity_summary,
    get_warehouse_temperature_summary,
    revoke_warehouse_manager,
    set_warehouse_maintenance,
    suspend_warehouse,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [HasWarehousePermission]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["warehouses.create"]

        elif self.action in [
            "update",
            "partial_update",
            "destroy",
            "activate",
            "suspend",
            "maintenance",
            "close",
        ]:
            self.required_permissions = ["warehouses.update"]

        else:
            self.required_permissions = ["warehouses.view"]

        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user

        queryset = Warehouse.objects.select_related(
            "organization",
            "facility",
            "country",
            "created_by",
        )

        if not user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                user,
                permission_code="warehouses.view",
            )

            queryset = queryset.filter(
                organization_id__in=organization_ids
            )

        status_filter = self.request.query_params.get("status")

        if status_filter:
            queryset = queryset.filter(
                status=status_filter.upper()
            )

        warehouse_type = self.request.query_params.get(
            "warehouse_type"
        )

        if warehouse_type:
            queryset = queryset.filter(
                warehouse_type=warehouse_type.upper()
            )

        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(city__icontains=search)
                | Q(administrative_area__icontains=search)
            )

        organization = self.request.query_params.get("organization")

        if organization:
            queryset = queryset.filter(
                organization_id=organization
            )

        facility = self.request.query_params.get("facility")

        if facility:
            queryset = queryset.filter(
                facility_id=facility
            )

        return queryset.distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data.get("organization")

        if not self.request.user.is_superuser:
            if not organization:
                raise ValidationError({
                    "organization": "Organization is required."
                })

            from apps.accounts.services import user_has_permission

            if not user_has_permission(
                self.request.user,
                "warehouses.create",
                organization=organization,
            ):
                raise ValidationError(
                    "You cannot create warehouses in this organization."
                )

        warehouse = serializer.save(
            created_by=self.request.user,
            status=WarehouseStatus.DRAFT,
        )

        from apps.warehouses.services import audit_warehouse

        audit_warehouse(
            request=self.request,
            action="WAREHOUSE_CREATED",
            warehouse=warehouse,
            description=f"Warehouse {warehouse.code} created.",
        )

    def perform_update(self, serializer):
        warehouse = self.get_object()

        old_name = warehouse.name
        old_address = warehouse.address
        old_capacity = warehouse.total_capacity

        warehouse = serializer.save()

        changes = {}

        if old_name != warehouse.name:
            changes["name"] = {
                "old": old_name,
                "new": warehouse.name,
            }

        if old_address != warehouse.address:
            changes["address"] = {
                "old": old_address,
                "new": warehouse.address,
            }

        if old_capacity != warehouse.total_capacity:
            changes["total_capacity"] = {
                "old": str(old_capacity),
                "new": str(warehouse.total_capacity),
            }

        from apps.warehouses.services import audit_warehouse

        audit_warehouse(
            request=self.request,
            action="WAREHOUSE_UPDATED",
            warehouse=warehouse,
            description=f"Warehouse {warehouse.code} updated.",
            changes=changes,
        )

    def destroy(self, request, *args, **kwargs):
        raise ValidationError(
            "Warehouses cannot be deleted. Use the close workflow."
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        warehouse = self.get_object()

        try:
            warehouse = activate_warehouse(
                warehouse_id=warehouse.pk,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(warehouse).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        warehouse = self.get_object()

        reason = request.data.get("reason", "").strip()

        if not reason:
            raise ValidationError({
                "reason": "Suspension reason is required."
            })

        try:
            warehouse = suspend_warehouse(
                warehouse_id=warehouse.pk,
                reason=reason,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(warehouse).data)

    @action(detail=True, methods=["post"])
    def maintenance(self, request, pk=None):
        warehouse = self.get_object()

        reason = request.data.get("reason", "").strip()

        if not reason:
            raise ValidationError({
                "reason": "Maintenance reason is required."
            })

        try:
            warehouse = set_warehouse_maintenance(
                warehouse_id=warehouse.pk,
                reason=reason,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(warehouse).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        warehouse = self.get_object()

        reason = request.data.get("reason", "").strip()

        if not reason:
            raise ValidationError({
                "reason": "Closure reason is required."
            })

        try:
            warehouse = close_warehouse(
                warehouse_id=warehouse.pk,
                reason=reason,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(warehouse).data)

    @action(detail=True, methods=["get"])
    def temperature_summary(self, request, pk=None):
        warehouse = self.get_object()

        return Response(
            get_warehouse_temperature_summary(warehouse)
        )

    @action(detail=True, methods=["get"])
    def capacity_summary(self, request, pk=None):
        warehouse = self.get_object()

        return Response(
            get_warehouse_capacity_summary(warehouse)
        )


class WarehouseRelatedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasWarehousePermission]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["warehouses.create"]

        elif self.action in [
            "update",
            "partial_update",
            "destroy",
            "revoke",
        ]:
            self.required_permissions = ["warehouses.update"]

        else:
            self.required_permissions = ["warehouses.view"]

        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="warehouses.view",
        )

        return queryset.filter(
            warehouse__organization_id__in=organization_ids
        ).distinct()

    def perform_create(self, serializer):
        warehouse = serializer.validated_data.get("warehouse")

        if not warehouse:
            raise ValidationError({
                "warehouse": "Warehouse is required."
            })

        if not self.request.user.is_superuser:
            from apps.accounts.services import user_has_permission

            if not user_has_permission(
                self.request.user,
                "warehouses.create",
                organization=warehouse.organization,
            ):
                raise ValidationError(
                    "You cannot manage this warehouse."
                )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        raise ValidationError(
            "Warehouse history cannot be deleted through this API."
        )


class StorageZoneViewSet(WarehouseRelatedViewSet):
    queryset = StorageZone.objects.select_related("warehouse")
    serializer_class = StorageZoneSerializer


class StorageLocationViewSet(WarehouseRelatedViewSet):
    queryset = StorageLocation.objects.select_related(
        "zone",
        "zone__warehouse",
    )
    serializer_class = StorageLocationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        zone_id = self.request.query_params.get("zone")

        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)

        return queryset


class WarehouseManagerViewSet(WarehouseRelatedViewSet):
    queryset = WarehouseManagerAssignment.objects.select_related(
        "warehouse",
        "user",
        "assigned_by",
    )
    serializer_class = WarehouseManagerAssignmentSerializer

    def perform_create(self, serializer):
        warehouse = serializer.validated_data["warehouse"]
        user = serializer.validated_data["user"]

        if not self.request.user.is_superuser:
            from apps.accounts.services import user_has_permission

            if not user_has_permission(
                self.request.user,
                "warehouses.update",
                organization=warehouse.organization,
            ):
                raise ValidationError(
                    "You cannot assign managers in this organization."
                )

        try:
            assign_warehouse_manager(
                warehouse=warehouse,
                user=user,
                assigned_by=self.request.user,
                valid_from=serializer.validated_data.get("valid_from"),
                valid_until=serializer.validated_data.get("valid_until"),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        assignment = self.get_object()

        try:
            assignment = revoke_warehouse_manager(
                assignment_id=assignment.pk
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(assignment).data
        )


class WarehouseTemperatureViewSet(WarehouseRelatedViewSet):
    queryset = WarehouseTemperatureReading.objects.select_related(
        "warehouse",
        "zone",
        "recorded_by",
    )
    serializer_class = WarehouseTemperatureReadingSerializer

    def perform_create(self, serializer):
        warehouse = serializer.validated_data["warehouse"]

        if warehouse.status == WarehouseStatus.CLOSED:
            raise ValidationError(
                "Cannot record readings for a closed warehouse."
            )

        serializer.save(recorded_by=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()

        warehouse_id = self.request.query_params.get("warehouse")

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        zone_id = self.request.query_params.get("zone")

        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)

        return queryset


class WarehouseCapacityViewSet(WarehouseRelatedViewSet):
    queryset = WarehouseCapacitySnapshot.objects.select_related(
        "warehouse",
        "recorded_by",
    )
    serializer_class = WarehouseCapacitySnapshotSerializer

    def perform_create(self, serializer):
        warehouse = serializer.validated_data["warehouse"]

        if warehouse.status == WarehouseStatus.CLOSED:
            raise ValidationError(
                "Cannot record capacity for a closed warehouse."
            )

        serializer.save(recorded_by=self.request.user)