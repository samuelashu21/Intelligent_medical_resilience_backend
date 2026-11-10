from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission

from apps.procurement.models import (
    PurchaseRequisition,
    SupplierQuotation,
    PurchaseOrder,
)

from apps.procurement.permissions import HasProcurementPermission

from apps.procurement.serializers import (
    PurchaseRequisitionSerializer,
    PurchaseRequisitionCreateSerializer,
    SupplierQuotationSerializer,
    SupplierQuotationCreateSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer,
    SupplierSelectionSerializer,
)

from apps.procurement.services import (
    create_purchase_requisition,
    submit_purchase_requisition,
    approve_purchase_requisition,
    add_supplier_quotation,
    select_supplier_quotation,
    create_purchase_order,
    submit_purchase_order_for_approval,
    approve_purchase_order,
    send_purchase_order,
    acknowledge_purchase_order,
)

# ============================================================
# VALIDATION ERROR CONVERSION
# ============================================================


def convert_validation_error(exc):
    if hasattr(exc, "messages"):
        return ValidationError(exc.messages)

    return ValidationError(str(exc))


# ============================================================
# BASE PROCUREMENT VIEWSET
# ============================================================


class ProcurementScopedViewSet(viewsets.GenericViewSet):

    permission_classes = [HasProcurementPermission]

    def get_scoped_organization_ids(self, permission_code):
        return get_user_accessible_organization_ids(
            self.request.user,
            permission_code=permission_code,
        )

    def check_organization_permission(
        self,
        organization,
        permission_code,
    ):
        if self.request.user.is_superuser:
            return

        if not user_has_permission(
            self.request.user,
            permission_code,
            organization=organization,
        ):
            raise PermissionDenied(
                "You do not have procurement access to this organization."
            )


# ============================================================
# PURCHASE REQUISITION VIEWSET
# ============================================================


class PurchaseRequisitionViewSet(ProcurementScopedViewSet):

    def get_queryset(self):
        queryset = PurchaseRequisition.objects.select_related(
            "replenishment_request",
            "organization",
            "requested_by",
            "approved_by",
        ).prefetch_related("items")

        if self.request.user.is_superuser:
            return queryset

        organization_ids = self.get_scoped_organization_ids(
            "procurement.requisition.view"
        )

        return queryset.filter(organization_id__in=organization_ids)

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseRequisitionCreateSerializer

        return PurchaseRequisitionSerializer

    def get_permissions(self):
        mapping = {
            "create": "procurement.requisition.create",
            "submit": "procurement.requisition.submit",
            "approve": "procurement.requisition.approve",
        }

        self.required_permissions = [
            mapping.get(
                self.action,
                "procurement.requisition.view",
            )
        ]

        return super().get_permissions()

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = PurchaseRequisitionSerializer(
                page,
                many=True,
            )

            return self.get_paginated_response(serializer.data)

        return Response(
            PurchaseRequisitionSerializer(
                queryset,
                many=True,
            ).data
        )

    def retrieve(self, request, pk=None):
        obj = self.get_object()

        return Response(PurchaseRequisitionSerializer(obj).data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_id = serializer.validated_data["replenishment_request"]

        try:
            from apps.replenishment.models import ReplenishmentRequest

            source = ReplenishmentRequest.objects.get(pk=request_id)

            self.check_organization_permission(
                source.organization,
                "procurement.requisition.create",
            )

            requisition = create_purchase_requisition(
                replenishment_request_id=request_id,
                user=request.user,
                justification=serializer.validated_data.get("justification"),
                notes=serializer.validated_data.get(
                    "notes",
                    "",
                ),
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(
            PurchaseRequisitionSerializer(requisition).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        requisition = self.get_object()

        self.check_organization_permission(
            requisition.organization,
            "procurement.requisition.submit",
        )

        try:
            result = submit_purchase_requisition(
                requisition.pk,
                request.user,
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(PurchaseRequisitionSerializer(result).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        requisition = self.get_object()

        self.check_organization_permission(
            requisition.organization,
            "procurement.requisition.approve",
        )

        try:
            result = approve_purchase_requisition(
                requisition.pk,
                request.user,
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(PurchaseRequisitionSerializer(result).data)


# ============================================================
# SUPPLIER QUOTATION VIEWSET
# ============================================================


class SupplierQuotationViewSet(ProcurementScopedViewSet):

    def get_queryset(self):
        queryset = SupplierQuotation.objects.select_related(
            "requisition",
            "requisition__organization",
            "supplier",
            "submitted_by",
        ).prefetch_related("items")

        if self.request.user.is_superuser:
            return queryset

        organization_ids = self.get_scoped_organization_ids(
            "procurement.quotation.view"
        )

        return queryset.filter(requisition__organization_id__in=organization_ids)

    def get_serializer_class(self):
        if self.action == "create":
            return SupplierQuotationCreateSerializer

        return SupplierQuotationSerializer

    def get_permissions(self):
        mapping = {
            "create": "procurement.quotation.create",
            "select": "procurement.quotation.select",
        }

        self.required_permissions = [
            mapping.get(
                self.action,
                "procurement.quotation.view",
            )
        ]

        return super().get_permissions()

    def list(self, request):
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)

        if page is not None:
            return self.get_paginated_response(
                SupplierQuotationSerializer(
                    page,
                    many=True,
                ).data
            )

        return Response(
            SupplierQuotationSerializer(
                queryset,
                many=True,
            ).data
        )

    def retrieve(self, request, pk=None):
        return Response(SupplierQuotationSerializer(self.get_object()).data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            requisition = PurchaseRequisition.objects.get(pk=data["requisition"])

            self.check_organization_permission(
                requisition.organization,
                "procurement.quotation.create",
            )

            quotation = add_supplier_quotation(
                requisition_id=data["requisition"],
                supplier_id=data["supplier"],
                quotation_number=data["quotation_number"],
                currency=data["currency"],
                valid_until=data["valid_until"],
                delivery_days=data["delivery_days"],
                submitted_by=request.user,
                items=data["items"],
                quotation_date=data.get("quotation_date"),
                payment_terms=data.get("payment_terms", ""),
                delivery_terms=data.get("delivery_terms", ""),
                notes=data.get("notes", ""),
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(
            SupplierQuotationSerializer(quotation).data,
            status=status.HTTP_201_CREATED,
        )

    # --------------------------------------------------------
    # COMPARE SUPPLIER QUOTATIONS
    # --------------------------------------------------------

    @action(detail=False, methods=["get"])
    def compare(self, request):

        requisition_id = request.query_params.get("requisition")

        if not requisition_id:
            raise ValidationError({"requisition": "This query parameter is required."})

        # get_queryset() enforces organization-level visibility.
        quotations = (
            self.get_queryset()
            .filter(
                requisition_id=requisition_id,
                status__in=[
                    "RECEIVED",
                    "UNDER_REVIEW",
                ],
            )
            .prefetch_related("items")
        )

        if not quotations.exists():
            return Response(
                {"detail": "No eligible quotations were found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        currencies = set(quotations.values_list("currency", flat=True))

        # Do not compare prices across different currencies.
        if len(currencies) > 1:
            return Response(
                {
                    "detail": (
                        "Quotations use different currencies. "
                        "Convert them using an approved exchange-rate "
                        "source before comparing total prices."
                    ),
                    "currencies": sorted(currencies),
                    "results": [],
                }
            )

        from apps.procurement.services import (
            calculate_quotation_total,
        )

        results = []

        for quotation in quotations:
            results.append(
                {
                    "quotation_id": str(quotation.pk),
                    "quotation_number": quotation.quotation_number,
                    "supplier": quotation.supplier.name,
                    "currency": quotation.currency,
                    "total": str(calculate_quotation_total(quotation)),
                    "delivery_days": quotation.delivery_days,
                    "valid_until": quotation.valid_until.isoformat(),
                }
            )

        # Lowest total first, then shortest delivery time.
        results.sort(
            key=lambda item: (
                Decimal(item["total"]),
                item["delivery_days"],
            )
        )

        return Response(
            {
                "requisition": requisition_id,
                "currency": next(iter(currencies)),
                "comparison": results,
                "selection_notice": (
                    "The lowest price is not automatically the best "
                    "supplier. Review delivery, quality, availability, "
                    "and contractual terms before selection."
                ),
            }
        )

    # --------------------------------------------------------
    # SELECT SUPPLIER QUOTATION
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def select(self, request, pk=None):
        quotation = self.get_object()

        self.check_organization_permission(
            quotation.requisition.organization,
            "procurement.quotation.select",
        )

        serializer = SupplierSelectionSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        try:
            result = select_supplier_quotation(
                quotation_id=quotation.pk,
                user=request.user,
                justification=serializer.validated_data["justification"],
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(SupplierQuotationSerializer(result).data)


# ============================================================
# PURCHASE ORDER VIEWSET
# ============================================================


class PurchaseOrderViewSet(ProcurementScopedViewSet):

    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related(
            "requisition",
            "quotation",
            "supplier",
            "organization",
            "created_by",
            "approved_by",
        ).prefetch_related("items")

        if self.request.user.is_superuser:
            return queryset

        organization_ids = self.get_scoped_organization_ids("procurement.order.view")

        return queryset.filter(organization_id__in=organization_ids)

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseOrderCreateSerializer

        return PurchaseOrderSerializer

    def get_permissions(self):
        mapping = {
            "create": "procurement.order.create",
            "submit": "procurement.order.submit",
            "approve": "procurement.order.approve",
            "send": "procurement.order.send",
            "acknowledge": "procurement.order.acknowledge",
        }

        self.required_permissions = [
            mapping.get(
                self.action,
                "procurement.order.view",
            )
        ]

        return super().get_permissions()

    def list(self, request):
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)

        if page is not None:
            return self.get_paginated_response(
                PurchaseOrderSerializer(
                    page,
                    many=True,
                ).data
            )

        return Response(
            PurchaseOrderSerializer(
                queryset,
                many=True,
            ).data
        )

    def retrieve(self, request, pk=None):
        return Response(PurchaseOrderSerializer(self.get_object()).data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            quotation = SupplierQuotation.objects.select_related(
                "requisition__organization"
            ).get(pk=data["quotation"])

            self.check_organization_permission(
                quotation.requisition.organization,
                "procurement.order.create",
            )

            order = create_purchase_order(
                quotation_id=quotation.pk,
                user=request.user,
                tax_amount=data.get(
                    "tax_amount",
                    0,
                ),
                shipping_amount=data.get(
                    "shipping_amount",
                    0,
                ),
                expected_delivery_date=data.get("expected_delivery_date"),
                notes=data.get("notes", ""),
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(
            PurchaseOrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        order = self.get_object()

        self.check_organization_permission(
            order.organization,
            "procurement.order.submit",
        )

        try:
            result = submit_purchase_order_for_approval(
                order.pk,
                request.user,
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(PurchaseOrderSerializer(result).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        order = self.get_object()

        self.check_organization_permission(
            order.organization,
            "procurement.order.approve",
        )

        try:
            result = approve_purchase_order(
                order.pk,
                request.user,
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(PurchaseOrderSerializer(result).data)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        order = self.get_object()

        self.check_organization_permission(
            order.organization,
            "procurement.order.send",
        )

        try:
            result = send_purchase_order(
                order.pk,
                request.user,
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(PurchaseOrderSerializer(result).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        order = self.get_object()

        self.check_organization_permission(
            order.organization,
            "procurement.order.acknowledge",
        )

        try:
            result = acknowledge_purchase_order(
                order.pk,
                request.user,
            )

        except DjangoValidationError as exc:
            raise convert_validation_error(exc)

        return Response(PurchaseOrderSerializer(result).data)
