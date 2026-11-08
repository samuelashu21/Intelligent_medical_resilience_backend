# from django.core.exceptions import ValidationError as DjangoValidationError
# from django.db.models import Q

# from rest_framework import status, viewsets
# from rest_framework.decorators import action
# from rest_framework.exceptions import ValidationError
# from rest_framework.response import Response

# from apps.accounts.scope_services import (
#     get_user_accessible_organization_ids,
# )

# from apps.inventory.models import (
#     InventoryBalance,
#     MovementType,
#     ReservationStatus,
#     StockBatch,
#     StockMovement,
#     StockReservation,
# )

# from apps.inventory.permissions import HasInventoryPermission

# from apps.inventory.serializers import (
#     InventoryBalanceSerializer,
#     StockBatchSerializer,
#     StockMovementSerializer,
#     StockReservationSerializer,
# )

# from apps.inventory.services import (
#     adjust_stock,
#     fulfill_reservation,
#     get_expiring_batches,
#     get_fefo_batches,
#     issue_stock,
#     receive_stock,
#     release_reservation,
#     reserve_stock,
# )


# class InventoryScopedViewSet(viewsets.GenericViewSet):
#     permission_classes = [HasInventoryPermission]

#     def get_accessible_organization_ids(self):
#         if self.request.user.is_superuser:
#             return None

#         return get_user_accessible_organization_ids(
#             self.request.user,
#             permission_code="inventory.view",
#         )

#     def filter_warehouse_scope(self, queryset, field="warehouse"):
#         organization_ids = self.get_accessible_organization_ids()

#         if organization_ids is None:
#             return queryset

#         return queryset.filter(
#             **{f"{field}__organization_id__in": organization_ids}
#         )


# class StockBatchViewSet(viewsets.ModelViewSet):
#     serializer_class = StockBatchSerializer
#     permission_classes = [HasInventoryPermission]

#     http_method_names = [
#         "get",
#         "post",
#         "patch",
#         "head",
#         "options",
#     ]

#     def get_permissions(self):
#         permission_map = {
#             "create": ["inventory.receive"],
#             "receive": ["inventory.receive"],
#             "issue": ["inventory.issue"],
#             "adjust": ["inventory.adjust"],
#             "update": ["inventory.adjust"],
#             "partial_update": ["inventory.adjust"],
#         }

#         self.required_permissions = permission_map.get(
#             self.action,
#             ["inventory.view"],
#         )

#         return super().get_permissions()

#     def check_inventory_scope(self, batch, permission_code):
#         if self.request.user.is_superuser:
#             return

#         from apps.accounts.services import user_has_permission

#         if not user_has_permission(
#             self.request.user,
#             permission_code,
#             organization=batch.warehouse.organization,
#         ):
#             raise ValidationError(
#                 "You do not have permission to perform this operation "
#                 "in this warehouse."
#             )

#     def get_queryset(self):
#         queryset = StockBatch.objects.select_related(
#             "medicine",
#             "presentation",
#             "warehouse",
#             "location",
#             "supplier",
#         )

#         if not self.request.user.is_superuser:
#             organization_ids = get_user_accessible_organization_ids(
#                 self.request.user,
#                 permission_code="inventory.view",
#             )

#             queryset = queryset.filter(
#                 warehouse__organization_id__in=organization_ids
#             )

#         medicine = self.request.query_params.get("medicine")

#         if medicine:
#             queryset = queryset.filter(medicine_id=medicine)

#         warehouse = self.request.query_params.get("warehouse")

#         if warehouse:
#             queryset = queryset.filter(warehouse_id=warehouse)

#         status_filter = self.request.query_params.get("status")

#         if status_filter:
#             queryset = queryset.filter(status=status_filter.upper())

#         search = self.request.query_params.get("search")

#         if search:
#             queryset = queryset.filter(
#                 Q(batch_number__icontains=search)
#                 | Q(medicine__generic_name__icontains=search)
#             )

#         return queryset.distinct()

#     def perform_create(self, serializer):
#         batch = serializer.save()

#         # Start with a zero balance. Actual stock enters through
#         # the receipt endpoint, not by creating a batch.
#         InventoryBalance.objects.get_or_create(batch=batch)

#     def update(self, request, *args, **kwargs):
#         raise ValidationError(
#             "Batch identity and location cannot be changed through this API. "
#             "Use an authorized inventory workflow."
#         )

#     def partial_update(self, request, *args, **kwargs):
#         raise ValidationError(
#             "Batch identity and location cannot be changed through this API."
#         )

#     def destroy(self, request, *args, **kwargs):
#         raise ValidationError(
#             "Stock batches cannot be deleted."
#         )

#     @action(detail=True, methods=["post"])
#     def receive(self, request, pk=None):
#         batch = self.get_object()
#         self.check_inventory_scope(batch, "inventory.receive")

#         try:
#             movement = receive_stock(
#                 batch_id=batch.pk,
#                 quantity=request.data.get("quantity"),
#                 performed_by=request.user,
#                 reference_number=request.data.get(
#                     "reference_number", ""
#                 ),
#                 notes=request.data.get("notes", ""),
#                 request=request,
#             )
#         except (DjangoValidationError, ValueError, TypeError) as exc:
#             if isinstance(exc, DjangoValidationError):
#                 raise ValidationError(exc.messages)
#             raise ValidationError(str(exc))

#         return Response(
#             StockMovementSerializer(movement).data,
#             status=status.HTTP_201_CREATED,
#         )

#     @action(detail=True, methods=["post"])
#     def issue(self, request, pk=None):
#         batch = self.get_object()
#         self.check_inventory_scope(batch, "inventory.issue")

#         try:
#             movement = issue_stock(
#                 batch_id=batch.pk,
#                 quantity=request.data.get("quantity"),
#                 performed_by=request.user,
#                 reference_number=request.data.get(
#                     "reference_number", ""
#                 ),
#                 notes=request.data.get("notes", ""),
#                 request=request,
#             )
#         except (DjangoValidationError, ValueError, TypeError) as exc:
#             if isinstance(exc, DjangoValidationError):
#                 raise ValidationError(exc.messages)
#             raise ValidationError(str(exc))

#         return Response(
#             StockMovementSerializer(movement).data,
#             status=status.HTTP_201_CREATED,
#         )

#     @action(detail=True, methods=["post"])
#     def adjust(self, request, pk=None):
#         batch = self.get_object()
#         self.check_inventory_scope(batch, "inventory.adjust")

#         try:
#             movement = adjust_stock(
#                 batch_id=batch.pk,
#                 quantity=request.data.get("quantity"),
#                 direction=request.data.get("direction"),
#                 performed_by=request.user,
#                 reason=request.data.get("reason", ""),
#                 reference_number=request.data.get(
#                     "reference_number", ""
#                 ),
#                 request=request,
#             )
#         except (DjangoValidationError, ValueError, TypeError) as exc:
#             if isinstance(exc, DjangoValidationError):
#                 raise ValidationError(exc.messages)
#             raise ValidationError(str(exc))

#         return Response(
#             StockMovementSerializer(movement).data,
#             status=status.HTTP_201_CREATED,
#         )


# class InventoryBalanceViewSet(viewsets.ReadOnlyModelViewSet):
#     serializer_class = InventoryBalanceSerializer
#     permission_classes = [HasInventoryPermission]

#     required_permissions = ["inventory.view"]

#     queryset = InventoryBalance.objects.select_related(
#         "batch",
#         "batch__medicine",
#         "batch__warehouse",
#         "batch__location",
#     )

#     def get_queryset(self):
#         queryset = super().get_queryset()

#         if not self.request.user.is_superuser:
#             organization_ids = get_user_accessible_organization_ids(
#                 self.request.user,
#                 permission_code="inventory.view",
#             )

#             queryset = queryset.filter(
#                 batch__warehouse__organization_id__in=organization_ids
#             )

#         medicine = self.request.query_params.get("medicine")
#         warehouse = self.request.query_params.get("warehouse")

#         if medicine:
#             queryset = queryset.filter(
#                 batch__medicine_id=medicine
#             )

#         if warehouse:
#             queryset = queryset.filter(
#                 batch__warehouse_id=warehouse
#             )

#         return queryset


# class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
#     serializer_class = StockMovementSerializer
#     permission_classes = [HasInventoryPermission]

#     required_permissions = ["inventory.view"]

#     queryset = StockMovement.objects.select_related(
#         "batch",
#         "batch__medicine",
#         "performed_by",
#         "source_warehouse",
#         "destination_warehouse",
#     )

#     def get_queryset(self):
#         queryset = super().get_queryset()

#         if not self.request.user.is_superuser:
#             organization_ids = get_user_accessible_organization_ids(
#                 self.request.user,
#                 permission_code="inventory.view",
#             )

#             queryset = queryset.filter(
#                 batch__warehouse__organization_id__in=organization_ids
#             )

#         batch = self.request.query_params.get("batch")

#         if batch:
#             queryset = queryset.filter(batch_id=batch)

#         movement_type = self.request.query_params.get("movement_type")

#         if movement_type:
#             queryset = queryset.filter(
#                 movement_type=movement_type.upper()
#             )

#         return queryset


# class StockReservationViewSet(viewsets.ModelViewSet):
#     serializer_class = StockReservationSerializer
#     permission_classes = [HasInventoryPermission]

#     http_method_names = [
#         "get",
#         "post",
#         "head",
#         "options",
#     ]

#     def get_permissions(self):
#         if self.action == "create":
#             self.required_permissions = ["inventory.issue"]
#         else:
#             self.required_permissions = ["inventory.view"]

#         return super().get_permissions()

#     def get_queryset(self):
#         queryset = StockReservation.objects.select_related(
#             "batch",
#             "batch__medicine",
#             "batch__warehouse",
#             "reserved_by",
#         )

#         if not self.request.user.is_superuser:
#             organization_ids = get_user_accessible_organization_ids(
#                 self.request.user,
#                 permission_code="inventory.view",
#             )

#             queryset = queryset.filter(
#                 batch__warehouse__organization_id__in=organization_ids
#             )

#         return queryset

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         batch = serializer.validated_data["batch"]

#         if not request.user.is_superuser:
#             from apps.accounts.services import user_has_permission

#             if not user_has_permission(
#                 request.user,
#                 "inventory.issue",
#                 organization=batch.warehouse.organization,
#             ):
#                 raise ValidationError(
#                     "You cannot reserve stock in this organization."
#                 )

#         from apps.inventory.services import reserve_stock

#         try:
#             reservation = reserve_stock(
#                 batch_id=batch.pk,
#                 quantity=serializer.validated_data["quantity"],
#                 reference_number=serializer.validated_data[
#                     "reference_number"
#                 ],
#                 reserved_by=request.user,
#                 purpose=serializer.validated_data.get("purpose", ""),
#                 expires_at=serializer.validated_data.get("expires_at"),
#             )
#         except (DjangoValidationError, ValueError, TypeError) as exc:
#             if isinstance(exc, DjangoValidationError):
#                 raise ValidationError(exc.messages)
#             raise ValidationError(str(exc))

#         return Response(
#             self.get_serializer(reservation).data,
#             status=status.HTTP_201_CREATED,
#         )

#     @action(detail=True, methods=["post"])
#     def release(self, request, pk=None):
#         reservation = self.get_object()

#         try:
#             reservation = release_reservation(
#                 reservation_id=reservation.pk
#             )
#         except DjangoValidationError as exc:
#             raise ValidationError(exc.messages)

#         return Response(self.get_serializer(reservation).data)

#     @action(detail=True, methods=["post"])
#     def fulfill(self, request, pk=None):
#         reservation = self.get_object()

#         try:
#             movement = fulfill_reservation(
#                 reservation_id=reservation.pk,
#                 performed_by=request.user,
#                 request=request,
#             )
#         except DjangoValidationError as exc:
#             raise ValidationError(exc.messages)

#         return Response(
#             StockMovementSerializer(movement).data,
#             status=status.HTTP_201_CREATED,
#         )


# class InventoryReportViewSet(InventoryScopedViewSet):
#     permission_classes = [HasInventoryPermission]

#     required_permissions = ["inventory.view"]

#     @action(detail=False, methods=["get"])
#     def expiring(self, request):
#         days = request.query_params.get("days", "90")

#         try:
#             days = int(days)
#         except (ValueError, TypeError):
#             raise ValidationError({
#                 "days": "Must be an integer."
#             })

#         if days < 0 or days > 3650:
#             raise ValidationError({
#                 "days": "Days must be between 0 and 3650."
#             })

#         queryset = get_expiring_batches(days=days)

#         if not request.user.is_superuser:
#             organization_ids = get_user_accessible_organization_ids(
#                 request.user,
#                 permission_code="inventory.view",
#             )

#             queryset = queryset.filter(
#                 warehouse__organization_id__in=organization_ids
#             )

#         return Response(
#             StockBatchSerializer(queryset, many=True).data
#         )

#     @action(detail=False, methods=["get"])
#     def fefo(self, request):
#         medicine_id = request.query_params.get("medicine")
#         warehouse_id = request.query_params.get("warehouse")
#         presentation_id = request.query_params.get("presentation")

#         if not medicine_id or not warehouse_id:
#             raise ValidationError({
#                 "detail": "medicine and warehouse are required."
#             })

#         if not request.user.is_superuser:
#             from apps.accounts.services import user_has_permission

#             from apps.warehouses.models import Warehouse

#             warehouse = Warehouse.objects.filter(
#                 pk=warehouse_id
#             ).first()

#             if not warehouse or not user_has_permission(
#                 request.user,
#                 "inventory.view",
#                 organization=warehouse.organization,
#             ):
#                 raise ValidationError(
#                     "You cannot view stock in this warehouse."
#                 )

#         batches = get_fefo_batches(
#             medicine_id=medicine_id,
#             warehouse_id=warehouse_id,
#             presentation_id=presentation_id,
#         )

#         return Response(
#             StockBatchSerializer(batches, many=True).data
#         )






from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)

from apps.inventory.models import (
    InventoryBalance,
    MovementType,
    ReservationStatus,
    StockBatch,
    StockMovement,
    StockReservation,
)

from apps.inventory.permissions import HasInventoryPermission

from apps.inventory.serializers import (
    InventoryBalanceSerializer,
    StockBatchSerializer,
    StockMovementSerializer,
    StockReservationSerializer,
)

from apps.inventory.services import (
    adjust_stock,
    fulfill_reservation,
    get_expiring_batches,
    get_fefo_batches,
    issue_stock,
    receive_stock,
    release_reservation,
    reserve_stock,
)


class InventoryScopedViewSet(viewsets.GenericViewSet):
    permission_classes = [HasInventoryPermission]

    def get_accessible_organization_ids(self):
        if self.request.user.is_superuser:
            return None

        return get_user_accessible_organization_ids(
            self.request.user,
            permission_code="inventory.view",
        )

    def filter_warehouse_scope(self, queryset, field="warehouse"):
        organization_ids = self.get_accessible_organization_ids()

        if organization_ids is None:
            return queryset

        return queryset.filter(
            **{f"{field}__organization_id__in": organization_ids}
        )


class StockBatchViewSet(viewsets.ModelViewSet):
    serializer_class = StockBatchSerializer
    permission_classes = [HasInventoryPermission]

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def get_permissions(self):
        permission_map = {
            "create": ["inventory.receive"],
            "receive": ["inventory.receive"],
            "issue": ["inventory.issue"],
            "adjust": ["inventory.adjust"],
            "update": ["inventory.adjust"],
            "partial_update": ["inventory.adjust"],
        }

        self.required_permissions = permission_map.get(
            self.action,
            ["inventory.view"],
        )

        return super().get_permissions()

    def check_inventory_scope(self, batch, permission_code):
        if self.request.user.is_superuser:
            return

        from apps.accounts.services import user_has_permission

        if not user_has_permission(
            self.request.user,
            permission_code,
            organization=batch.warehouse.organization,
        ):
            raise ValidationError(
                "You do not have permission to perform this operation "
                "in this warehouse."
            )

    def get_queryset(self):
        queryset = StockBatch.objects.select_related(
            "medicine",
            "presentation",
            "warehouse",
            "location",
            "supplier",
        )

        if not self.request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                self.request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                warehouse__organization_id__in=organization_ids
            )

        medicine = self.request.query_params.get("medicine")

        if medicine:
            queryset = queryset.filter(medicine_id=medicine)

        warehouse = self.request.query_params.get("warehouse")

        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)

        status_filter = self.request.query_params.get("status")

        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(batch_number__icontains=search)
                | Q(medicine__generic_name__icontains=search)
            )

        return queryset.distinct()

    def perform_create(self, serializer):
        batch = serializer.save()

        # Start with a zero balance. Actual stock enters through
        # the receipt endpoint, not by creating a batch.
        InventoryBalance.objects.get_or_create(batch=batch)

    def update(self, request, *args, **kwargs):
        raise ValidationError(
            "Batch identity and location cannot be changed through this API. "
            "Use an authorized inventory workflow."
        )

    def partial_update(self, request, *args, **kwargs):
        raise ValidationError(
            "Batch identity and location cannot be changed through this API."
        )

    def destroy(self, request, *args, **kwargs):
        raise ValidationError(
            "Stock batches cannot be deleted."
        )

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None, **kwargs):
        batch = self.get_object()
        self.check_inventory_scope(batch, "inventory.receive")

        try:
            movement = receive_stock(
                batch_id=batch.pk,
                quantity=request.data.get("quantity"),
                performed_by=request.user,
                reference_number=request.data.get(
                    "reference_number", ""
                ),
                notes=request.data.get("notes", ""),
                request=request,
            )
        except (DjangoValidationError, ValueError, TypeError) as exc:
            if isinstance(exc, DjangoValidationError):
                raise ValidationError(exc.messages)
            raise ValidationError(str(exc))

        return Response(
            StockMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None, **kwargs):
        batch = self.get_object()
        self.check_inventory_scope(batch, "inventory.issue")

        try:
            movement = issue_stock(
                batch_id=batch.pk,
                quantity=request.data.get("quantity"),
                performed_by=request.user,
                reference_number=request.data.get(
                    "reference_number", ""
                ),
                notes=request.data.get("notes", ""),
                request=request,
            )
        except (DjangoValidationError, ValueError, TypeError) as exc:
            if isinstance(exc, DjangoValidationError):
                raise ValidationError(exc.messages)
            raise ValidationError(str(exc))

        return Response(
            StockMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None, **kwargs):
        batch = self.get_object()
        self.check_inventory_scope(batch, "inventory.adjust")

        try:
            movement = adjust_stock(
                batch_id=batch.pk,
                quantity=request.data.get("quantity"),
                direction=request.data.get("direction"),
                performed_by=request.user,
                reason=request.data.get("reason", ""),
                reference_number=request.data.get(
                    "reference_number", ""
                ),
                request=request,
            )
        except (DjangoValidationError, ValueError, TypeError) as exc:
            if isinstance(exc, DjangoValidationError):
                raise ValidationError(exc.messages)
            raise ValidationError(str(exc))

        return Response(
            StockMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )


class InventoryBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InventoryBalanceSerializer
    permission_classes = [HasInventoryPermission]

    required_permissions = ["inventory.view"]

    queryset = InventoryBalance.objects.select_related(
        "batch",
        "batch__medicine",
        "batch__warehouse",
        "batch__location",
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                self.request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                batch__warehouse__organization_id__in=organization_ids
            )

        medicine = self.request.query_params.get("medicine")
        warehouse = self.request.query_params.get("warehouse")

        if medicine:
            queryset = queryset.filter(
                batch__medicine_id=medicine
            )

        if warehouse:
            queryset = queryset.filter(
                batch__warehouse_id=warehouse
            )

        return queryset


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [HasInventoryPermission]

    required_permissions = ["inventory.view"]

    queryset = StockMovement.objects.select_related(
        "batch",
        "batch__medicine",
        "performed_by",
        "source_warehouse",
        "destination_warehouse",
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                self.request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                batch__warehouse__organization_id__in=organization_ids
            )

        batch = self.request.query_params.get("batch")

        if batch:
            queryset = queryset.filter(batch_id=batch)

        movement_type = self.request.query_params.get("movement_type")

        if movement_type:
            queryset = queryset.filter(
                movement_type=movement_type.upper()
            )

        return queryset


class StockReservationViewSet(viewsets.ModelViewSet):
    serializer_class = StockReservationSerializer
    permission_classes = [HasInventoryPermission]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["inventory.issue"]
        else:
            self.required_permissions = ["inventory.view"]

        return super().get_permissions()

    def get_queryset(self):
        queryset = StockReservation.objects.select_related(
            "batch",
            "batch__medicine",
            "batch__warehouse",
            "reserved_by",
        )

        if not self.request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                self.request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                batch__warehouse__organization_id__in=organization_ids
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        batch = serializer.validated_data["batch"]

        if not request.user.is_superuser:
            from apps.accounts.services import user_has_permission

            if not user_has_permission(
                request.user,
                "inventory.issue",
                organization=batch.warehouse.organization,
            ):
                raise ValidationError(
                    "You cannot reserve stock in this organization."
                )

        from apps.inventory.services import reserve_stock

        try:
            reservation = reserve_stock(
                batch_id=batch.pk,
                quantity=serializer.validated_data["quantity"],
                reference_number=serializer.validated_data[
                    "reference_number"
                ],
                reserved_by=request.user,
                purpose=serializer.validated_data.get("purpose", ""),
                expires_at=serializer.validated_data.get("expires_at"),
            )
        except (DjangoValidationError, ValueError, TypeError) as exc:
            if isinstance(exc, DjangoValidationError):
                raise ValidationError(exc.messages)
            raise ValidationError(str(exc))

        return Response(
            self.get_serializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None, **kwargs):
        reservation = self.get_object()

        try:
            reservation = release_reservation(
                reservation_id=reservation.pk
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(reservation).data)

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None, **kwargs):
        reservation = self.get_object()

        try:
            movement = fulfill_reservation(
                reservation_id=reservation.pk,
                performed_by=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            StockMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )


class InventoryReportViewSet(InventoryScopedViewSet):
    permission_classes = [HasInventoryPermission]

    required_permissions = ["inventory.view"]

    @action(detail=False, methods=["get"])
    def expiring(self, request, **kwargs):
        days = request.query_params.get("days", "90")

        try:
            days = int(days)
        except (ValueError, TypeError):
            raise ValidationError({
                "days": "Must be an integer."
            })

        if days < 0 or days > 3650:
            raise ValidationError({
                "days": "Days must be between 0 and 3650."
            })

        queryset = get_expiring_batches(days=days)

        if not request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                warehouse__organization_id__in=organization_ids
            )

        return Response(
            StockBatchSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"])
    def fefo(self, request, **kwargs):
        medicine_id = request.query_params.get("medicine")
        warehouse_id = request.query_params.get("warehouse")
        presentation_id = request.query_params.get("presentation")

        if not medicine_id or not warehouse_id:
            raise ValidationError({
                "detail": "medicine and warehouse are required."
            })

        if not request.user.is_superuser:
            from apps.accounts.services import user_has_permission

            from apps.warehouses.models import Warehouse

            warehouse = Warehouse.objects.filter(
                pk=warehouse_id
            ).first()

            if not warehouse or not user_has_permission(
                request.user,
                "inventory.view",
                organization=warehouse.organization,
            ):
                raise ValidationError(
                    "You cannot view stock in this warehouse."
                )

        batches = get_fefo_batches(
            medicine_id=medicine_id,
            warehouse_id=warehouse_id,
            presentation_id=presentation_id,
        )

        return Response(
            StockBatchSerializer(batches, many=True).data
        )