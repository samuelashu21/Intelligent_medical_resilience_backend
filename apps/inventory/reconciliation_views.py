from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission

from apps.inventory.models import (
    StockCount,
    StockCountLine,
    StockReconciliation,
)

from apps.inventory.permissions import HasInventoryPermission

from apps.inventory.reconciliation_services import (
    approve_stock_count,
    create_stock_count,
    post_stock_reconciliation,
    record_physical_count,
    reject_stock_count,
    start_stock_count,
    submit_stock_count,
)

from apps.inventory.reconciliation_serializers import (
    RecordPhysicalCountSerializer,
    StockCountLineSerializer,
    StockCountSerializer,
    StockReconciliationSerializer,
)


from rest_framework.views import APIView

from apps.inventory.reconciliation_reports import (
    get_reconciliation_summary,
)

class StockCountViewSet(viewsets.ModelViewSet):
    serializer_class = StockCountSerializer
    permission_classes = [HasInventoryPermission]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = StockCount.objects.select_related(
            "warehouse",
            "created_by",
            "approved_by",
        ).prefetch_related("lines")

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="inventory.view",
        )

        return queryset.filter(
            warehouse__organization_id__in=organization_ids
        )

    def get_permissions(self):
        permissions = {
            "list": ["inventory.view"],
            "retrieve": ["inventory.view"],
            "create": ["inventory.adjust"],
            "start": ["inventory.adjust"],
            "submit": ["inventory.adjust"],
            "approve": ["inventory.reconcile"],
            "reject": ["inventory.reconcile"],
            "post": ["inventory.reconcile"],
        }

        self.required_permissions = permissions.get(
            self.action,
            ["inventory.view"],
        )

        return super().get_permissions()

    def perform_create(self, serializer):
        warehouse = serializer.validated_data["warehouse"]

        if not user_has_permission(
            self.request.user,
            "inventory.adjust",
            organization=warehouse.organization,
        ):
            raise ValidationError(
                "You cannot create stock counts for this warehouse."
            )

        stock_count = create_stock_count(
            warehouse_id=warehouse.pk,
            reference_number=serializer.validated_data[
                "reference_number"
            ],
            created_by=self.request.user,
            count_method=serializer.validated_data.get(
                "count_method",
                "FULL",
            ),
            notes=serializer.validated_data.get("notes", ""),
        )

        serializer.instance = stock_count

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        stock_count = self.get_object()

        try:
            stock_count = start_stock_count(stock_count.pk)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(stock_count).data
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        stock_count = self.get_object()

        try:
            stock_count = submit_stock_count(
                stock_count.pk,
                submitted_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(stock_count).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        stock_count = self.get_object()

        if not user_has_permission(
            request.user,
            "inventory.reconcile",
            organization=stock_count.warehouse.organization,
        ):
            raise ValidationError(
                "You cannot approve stock counts for this warehouse."
            )

        try:
            stock_count = approve_stock_count(
                stock_count.pk,
                approved_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(stock_count).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        stock_count = self.get_object()

        if not user_has_permission(
            request.user,
            "inventory.reconcile",
            organization=stock_count.warehouse.organization,
        ):
            raise ValidationError(
                "You cannot reject stock counts for this warehouse."
            )

        try:
            stock_count = reject_stock_count(
                stock_count.pk,
                rejected_by=request.user,
                reason=request.data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(stock_count).data
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        stock_count = self.get_object()

        if not user_has_permission(
            request.user,
            "inventory.reconcile",
            organization=stock_count.warehouse.organization,
        ):
            raise ValidationError(
                "You cannot post reconciliation for this warehouse."
            )

        try:
            stock_count = post_stock_reconciliation(
                stock_count.pk,
                posted_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(stock_count).data
        )


class StockCountLineViewSet(viewsets.GenericViewSet):
    serializer_class = StockCountLineSerializer
    permission_classes = [HasInventoryPermission]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = StockCountLine.objects.select_related(
            "stock_count",
            "batch",
            "batch__warehouse",
            "batch__medicine",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="inventory.view",
        )

        return queryset.filter(
            stock_count__warehouse__organization_id__in=organization_ids
        )

    def get_permissions(self):
        self.required_permissions = (
            ["inventory.adjust"]
            if self.action == "record"
            else ["inventory.view"]
        )
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def record(self, request, pk=None):
        line = self.get_object()

        if not user_has_permission(
            request.user,
            "inventory.adjust",
            organization=line.stock_count.warehouse.organization,
        ):
            raise ValidationError(
                "You cannot record counts for this warehouse."
            )

        serializer = RecordPhysicalCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            line = record_physical_count(
                line_id=line.pk,
                physical_quantity=serializer.validated_data[
                    "physical_quantity"
                ],
                counted_by=request.user,
                reason=serializer.validated_data.get("reason", ""),
                explanation=serializer.validated_data.get(
                    "explanation", ""
                ),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(line).data,
            status=status.HTTP_200_OK,
        )


class StockReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockReconciliationSerializer
    permission_classes = [HasInventoryPermission]
    required_permissions = ["inventory.view"]

    def get_queryset(self):
        queryset = StockReconciliation.objects.select_related(
            "stock_count",
            "count_line",
            "count_line__batch",
            "posted_by",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="inventory.view",
        )

        return queryset.filter(
            stock_count__warehouse__organization_id__in=organization_ids
        )



class ReconciliationSummaryView(APIView):
    permission_classes = [HasInventoryPermission]
    required_permissions = ["inventory.view"]

    def get(self, request):
        organization_ids = None

        if not request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                request.user,
                permission_code="inventory.view",
            )

        warehouse_id = request.query_params.get("warehouse")

        if warehouse_id:
            # Confirm the requested warehouse is in the user's scope.
            from apps.warehouses.models import Warehouse

            warehouse = Warehouse.objects.filter(
                pk=warehouse_id,
            ).first()

            if not warehouse:
                return Response(
                    {"detail": "Warehouse not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if (
                not request.user.is_superuser
                and warehouse.organization_id not in organization_ids
            ):
                return Response(
                    {"detail": "You cannot access this warehouse."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        result = get_reconciliation_summary(
            organization_ids=organization_ids,
            warehouse_id=warehouse_id,
        )

        return Response(result)