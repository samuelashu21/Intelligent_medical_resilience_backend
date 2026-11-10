
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
)

from apps.logistics.shipment_models import (
    Transporter,
    Vehicle,
    Shipment,
    ShipmentDocument,
    ShipmentException,
)

from apps.logistics.shipment_services import (
    create_shipment,
    mark_shipment_ready,
    dispatch_shipment,
    update_shipment_tracking,
    report_shipment_delay,
    report_shipment_exception,
    resolve_shipment_exception,
    report_shipment_delivered,
)

from apps.logistics.shipment_serializers import (
    TransporterSerializer,
    VehicleSerializer,
    ShipmentSerializer,
    ShipmentCreateSerializer,
    ShipmentTrackingSerializer,
    ShipmentDelaySerializer,
    ShipmentExceptionCreateSerializer,
    ShipmentExceptionResolveSerializer,
    ShipmentDeliverySerializer,
    ShipmentDispatchSerializer,
    ShipmentDocumentSerializer,
)


from apps.logistics.document_validators import (
    validate_shipment_document,
)


def raise_api_validation_error(exc):
    raise ValidationError(
        getattr(exc, "messages", [str(exc)])
    )


class ShipmentViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ShipmentSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_required_permission(self):

        mapping = {
            "create_shipment": "logistics.shipment.create",
            "ready": "logistics.shipment.manage",
            "dispatch": "logistics.shipment.dispatch",
            "tracking": "logistics.shipment.track",
            "delay": "logistics.shipment.track",
            "exception": "logistics.shipment.exception.manage",
            "resolve_exception": "logistics.shipment.exception.manage",
            "exceptions": "logistics.shipment.view",
            "delivered": "logistics.shipment.deliver",
        }

        return mapping.get(
            self.action,
            "logistics.shipment.view",
        )

    def get_permissions(self):

        self.required_permissions = [
            self.get_required_permission()
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = (
            Shipment.objects
            .select_related(
                "transfer",
                "transfer__donor_facility",
                "transfer__recipient_facility",
                "transporter",
                "vehicle",
                "created_by",
            )
            .prefetch_related(
                "lines",
                "lines__medicine",
                "lines__batch",
                "events",
                "documents",
                "exceptions",
            )
        )

        if self.request.user.is_superuser:
            return queryset

        visible_ids = get_user_accessible_facility_ids(
            self.request.user,
            permission_code="logistics.shipment.view",
        )

        return queryset.filter(
            Q(transfer__donor_facility_id__in=visible_ids)
            & Q(transfer__recipient_facility_id__in=visible_ids)
        ).distinct()

    @action(
        detail=False,
        methods=["post"],
        url_path="create-shipment",
    )
    def create_shipment(self, request):

        serializer = ShipmentCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        values = serializer.validated_data

        try:

            shipment = create_shipment(
                transfer_id=values["transfer_id"],
                transporter_id=values["transporter_id"],
                vehicle_id=values["vehicle_id"],
                driver_name=values["driver_name"],
                driver_phone=values.get("driver_phone", ""),
                planned_dispatch_at=values.get(
                    "planned_dispatch_at"
                ),
                estimated_delivery_at=values.get(
                    "estimated_delivery_at"
                ),
                distance_km=values.get("distance_km"),
                transport_cost=values.get("transport_cost"),
                currency_code=values.get("currency_code", ""),
                user=request.user,
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response(
            ShipmentSerializer(shipment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def ready(self, request, pk=None):

        shipment = self.get_object()

        try:
            shipment = mark_shipment_ready(
                shipment_id=shipment.pk,
                user=request.user,
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response(
            ShipmentSerializer(shipment).data
        )

    @action(detail=True, methods=["post"])
    def dispatch(self, request, pk=None):

        serializer = ShipmentDispatchSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        shipment = self.get_object()

        try:

            shipment = dispatch_shipment(
                shipment_id=shipment.pk,
                user=request.user,
                dispatch_reference=serializer.validated_data.get(
                    "dispatch_reference",
                    "",
                ),
                dispatch_notes=serializer.validated_data.get(
                    "dispatch_notes",
                    "",
                ),
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response(
            ShipmentSerializer(shipment).data
        )

    @action(detail=True, methods=["post"])
    def tracking(self, request, pk=None):

        serializer = ShipmentTrackingSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        shipment = self.get_object()

        try:

            event = update_shipment_tracking(
                shipment_id=shipment.pk,
                user=request.user,
                **serializer.validated_data,
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        from apps.logistics.shipment_serializers import (
            ShipmentEventSerializer,
        )

        return Response(
            ShipmentEventSerializer(event).data
        )

    @action(detail=True, methods=["post"])
    def delay(self, request, pk=None):

        serializer = ShipmentDelaySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        shipment = self.get_object()

        try:

            shipment = report_shipment_delay(
                shipment_id=shipment.pk,
                user=request.user,
                description=serializer.validated_data[
                    "description"
                ],
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response(
            ShipmentSerializer(shipment).data
        )

    @action(detail=True, methods=["post"])
    def exception(self, request, pk=None):

        serializer = ShipmentExceptionCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        shipment = self.get_object()

        try:

            exception = report_shipment_exception(
                shipment_id=shipment.pk,
                user=request.user,
                **serializer.validated_data,
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response(
            {
                "id": str(exception.pk),
                "exception_type": exception.exception_type,
                "description": exception.description,
                "resolved": exception.resolved,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="exceptions/(?P<exception_id>[^/.]+)/resolve",
    )
    def resolve_exception(self, request, exception_id=None):

        serializer = ShipmentExceptionResolveSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            exception = resolve_shipment_exception(
                exception_id=exception_id,
                user=request.user,
                resolution_notes=serializer.validated_data[
                    "resolution_notes"
                ],
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response({
            "id": str(exception.pk),
            "resolved": exception.resolved,
            "resolution_notes": exception.resolution_notes,
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="exceptions",
    )
    def exceptions(self, request):

        queryset = (
            ShipmentException.objects
            .select_related(
                "shipment",
                "reported_by",
            )
            .order_by("-reported_at")
        )

        if not request.user.is_superuser:

            visible_ids = get_user_accessible_facility_ids(
                request.user,
                permission_code="logistics.shipment.view",
            )

            queryset = queryset.filter(
                shipment__transfer__donor_facility_id__in=visible_ids,
                shipment__transfer__recipient_facility_id__in=visible_ids,
            )

        from apps.logistics.shipment_serializers import (
            ShipmentExceptionSerializer,
        )

        page = self.paginate_queryset(queryset)

        if page is not None:

            serializer = ShipmentExceptionSerializer(
                page,
                many=True,
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = ShipmentExceptionSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="report-delivered",
    )
    def delivered(self, request, pk=None):

        serializer = ShipmentDeliverySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        shipment = self.get_object()

        try:

            shipment = report_shipment_delivered(
                shipment_id=shipment.pk,
                user=request.user,
                **serializer.validated_data,
            )

        except DjangoValidationError as exc:
            raise_api_validation_error(exc)

        return Response(
            ShipmentSerializer(shipment).data
        )


class TransporterViewSet(viewsets.ModelViewSet):

    serializer_class = TransporterSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_permissions(self):

        self.required_permissions = [
            (
                "logistics.transporter.manage"
                if self.action in [
                    "create",
                    "update",
                    "partial_update",
                    "destroy",
                ]
                else "logistics.transporter.view"
            )
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = Transporter.objects.all().select_related(
            "organization"
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = (
            self.request.user.role_assignments
            .filter(is_active=True)
            .values_list("organization_id", flat=True)
        )

        return queryset.filter(
            organization_id__in=organization_ids
        ).distinct()


class VehicleViewSet(viewsets.ModelViewSet):

    serializer_class = VehicleSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_permissions(self):

        self.required_permissions = [
            (
                "logistics.vehicle.manage"
                if self.action in [
                    "create",
                    "update",
                    "partial_update",
                    "destroy",
                ]
                else "logistics.vehicle.view"
            )
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = Vehicle.objects.select_related(
            "transporter",
            "transporter__organization",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = (
            self.request.user.role_assignments
            .filter(is_active=True)
            .values_list("organization_id", flat=True)
        )

        return queryset.filter(
            transporter__organization_id__in=organization_ids
        ).distinct()


class ShipmentDocumentViewSet(viewsets.ModelViewSet):

    serializer_class = ShipmentDocumentSerializer

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_permissions(self):

        self.required_permissions = [
            (
                "logistics.shipment.document.manage"
                if self.action in ["create", "destroy"]
                else "logistics.shipment.view"
            )
        ]

        return super().get_permissions()

    def get_queryset(self):

        queryset = ShipmentDocument.objects.select_related(
            "shipment",
            "shipment__transfer",
            "uploaded_by",
        )

        if self.request.user.is_superuser:
            return queryset

        visible_ids = get_user_accessible_facility_ids(
            self.request.user,
            permission_code="logistics.shipment.view",
        )

        return queryset.filter(
            shipment__transfer__donor_facility_id__in=visible_ids,
            shipment__transfer__recipient_facility_id__in=visible_ids,
        )

    def perform_create(self, serializer):

        uploaded_file = self.request.FILES.get("file")

        if not uploaded_file:
            raise ValidationError(
                "A document file is required."
            )

        validate_shipment_document(uploaded_file)

        shipment = serializer.validated_data["shipment"]

        if not self.request.user.is_superuser:

            visible_ids = get_user_accessible_facility_ids(
                self.request.user,
                permission_code="logistics.shipment.document.manage",
            )

            if (
                shipment.transfer.donor_facility_id not in visible_ids
                or shipment.transfer.recipient_facility_id not in visible_ids
            ):
                raise ValidationError(
                    "You cannot upload documents for this shipment."
                )

        serializer.save(
            uploaded_by=self.request.user
        )
