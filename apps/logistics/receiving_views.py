
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
)

from apps.facilities.models import Facility
from apps.warehouses.models import Warehouse

from apps.logistics.shipment_models import Shipment

from apps.logistics.receiving_models import (
    ReceivingRecord,
    ReceivingLine,
    ReceivingDiscrepancy,
    ReceivingStatus,
)

from apps.logistics.receiving_services import (
    create_receiving_record,
    record_received_line,
    submit_receiving_record,
    approve_receiving_record,
    reject_receiving_record,
    post_receiving_record,
    resolve_receiving_discrepancy,
)

from apps.logistics.receiving_serializers import (
    ReceivingRecordSerializer,
    ReceivingRecordCreateSerializer,
    ReceivingLineSerializer,
    ReceivingLineUpdateSerializer,
    ReceivingRejectSerializer,
    ReceivingDiscrepancySerializer,
    DiscrepancyResolveSerializer,
)


def raise_receiving_validation_error(exc):
    raise ValidationError(
        getattr(exc, "messages", [str(exc)])
    )


class ReceivingRecordViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ReceivingRecordSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_required_permission(self):

        mapping = {
            "create_receipt": "logistics.receiving.create",
            "record_line": "logistics.receiving.record",
            "submit": "logistics.receiving.submit",
            "approve": "logistics.receiving.approve",
            "reject": "logistics.receiving.approve",
            "post": "logistics.receiving.post",
        }

        return mapping.get(
            self.action,
            "logistics.receiving.view",
        )

    def get_permissions(self):

        self.required_permissions = [
            self.get_required_permission()
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = (
            ReceivingRecord.objects
            .select_related(
                "shipment",
                "recipient_facility",
                "receiving_warehouse",
                "received_by",
                "approved_by",
                "posted_by",
            )
            .prefetch_related(
                "lines",
                "lines__medicine",
                "lines__batch",
                "lines__discrepancies",
            )
        )

        if self.request.user.is_superuser:
            return queryset

        visible_ids = get_user_accessible_facility_ids(
            self.request.user,
            permission_code="logistics.receiving.view",
        )

        return queryset.filter(
            recipient_facility_id__in=visible_ids
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="create",
    )
    def create_receipt(self, request):

        serializer = ReceivingRecordCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        values = serializer.validated_data

        # Retrieve the warehouse and shipment before calling
        # the receiving service.
        try:

            warehouse = Warehouse.objects.get(
                pk=values["receiving_warehouse_id"],
            )

            shipment = (
                Shipment.objects
                .select_related(
                    "transfer",
                    "transfer__recipient_facility",
                )
                .get(
                    pk=values["shipment_id"],
                )
            )

        except Warehouse.DoesNotExist:
            raise ValidationError(
                "Receiving warehouse does not exist."
            )

        except Shipment.DoesNotExist:
            raise ValidationError(
                "Shipment does not exist."
            )

        # Enforce facility-level authorization.
        if not request.user.is_superuser:

            visible_ids = get_user_accessible_facility_ids(
                request.user,
                permission_code="logistics.receiving.create",
            )

            if shipment.transfer.recipient_facility_id not in visible_ids:
                raise ValidationError(
                    "You cannot create receipts for this recipient facility."
                )

            if warehouse.facility_id not in visible_ids:
                raise ValidationError(
                    "You cannot receive stock into this warehouse."
                )

        try:

            receipt = create_receiving_record(
                shipment_id=values["shipment_id"],
                receiving_warehouse=warehouse,
                user=request.user,
                notes=values.get("notes", ""),
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingRecordSerializer(receipt).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"lines/(?P<line_id>[^/.]+)/record",
    )
    def record_line(self, request, pk=None, line_id=None):

        receipt = self.get_object()

        serializer = ReceivingLineUpdateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            line = ReceivingLine.objects.get(
                pk=line_id,
                receiving_record=receipt,
            )

            line = record_received_line(
                receiving_line_id=line.pk,
                user=request.user,
                **serializer.validated_data,
            )

        except ReceivingLine.DoesNotExist:
            raise ValidationError(
                "Receiving line does not exist in this receipt."
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingLineSerializer(line).data
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):

        receipt = self.get_object()

        try:
            receipt = submit_receiving_record(
                receiving_record_id=receipt.pk,
                user=request.user,
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingRecordSerializer(receipt).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):

        receipt = self.get_object()

        try:
            receipt = approve_receiving_record(
                receiving_record_id=receipt.pk,
                user=request.user,
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingRecordSerializer(receipt).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):

        serializer = ReceivingRejectSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        receipt = self.get_object()

        try:
            receipt = reject_receiving_record(
                receiving_record_id=receipt.pk,
                user=request.user,
                reason=serializer.validated_data["reason"],
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingRecordSerializer(receipt).data
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):

        receipt = self.get_object()

        try:
            receipt = post_receiving_record(
                receiving_record_id=receipt.pk,
                user=request.user,
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingRecordSerializer(receipt).data
        )


class ReceivingDiscrepancyViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = ReceivingDiscrepancySerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_permissions(self):

        self.required_permissions = [
            (
                "logistics.receiving.discrepancy.manage"
                if self.action == "resolve"
                else "logistics.receiving.view"
            )
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = (
            ReceivingDiscrepancy.objects
            .select_related(
                "receiving_line",
                "receiving_line__receiving_record",
                "reported_by",
                "resolved_by",
            )
        )

        if self.request.user.is_superuser:
            return queryset

        visible_ids = get_user_accessible_facility_ids(
            self.request.user,
            permission_code="logistics.receiving.view",
        )

        return queryset.filter(
            receiving_line__receiving_record__recipient_facility_id__in=visible_ids
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):

        serializer = DiscrepancyResolveSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        discrepancy = self.get_object()

        try:

            discrepancy = resolve_receiving_discrepancy(
                discrepancy_id=discrepancy.pk,
                user=request.user,
                **serializer.validated_data,
            )

        except DjangoValidationError as exc:
            raise_receiving_validation_error(exc)

        return Response(
            ReceivingDiscrepancySerializer(
                discrepancy
            ).data
        )
