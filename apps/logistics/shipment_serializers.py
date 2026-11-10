from rest_framework import serializers

from apps.logistics.shipment_models import (
    Transporter,
    Vehicle,
    Shipment,
    ShipmentLine,
    ShipmentEvent,
    ShipmentDocument,
    ShipmentException,
)


class TransporterSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transporter
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class VehicleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vehicle
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class ShipmentLineSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    class Meta:
        model = ShipmentLine

        fields = [
            "id",
            "transfer_line",
            "medicine",
            "medicine_name",
            "batch",
            "batch_number",
            "dispatched_quantity",
            "unit_code",
        ]

        read_only_fields = fields


class ShipmentEventSerializer(serializers.ModelSerializer):

    recorded_by_email = serializers.CharField(
        source="recorded_by.email",
        read_only=True,
    )

    class Meta:
        model = ShipmentEvent

        fields = [
            "id",
            "event_type",
            "description",
            "latitude",
            "longitude",
            "recorded_by",
            "recorded_by_email",
            "event_time",
            "created_at",
        ]

        read_only_fields = fields


class ShipmentDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShipmentDocument

        fields = [
            "id",
            "shipment",
            "document_type",
            "file",
            "reference_number",
            "uploaded_by",
            "uploaded_at",
            "description",
        ]

        read_only_fields = [
            "id",
            "uploaded_by",
            "uploaded_at",
        ]


class ShipmentExceptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShipmentException

        fields = "__all__"

        read_only_fields = [
            "id",
            "reported_by",
            "reported_at",
            "resolved_by",
            "resolved_at",
        ]


class ShipmentSerializer(serializers.ModelSerializer):

    shipment_lines = ShipmentLineSerializer(
        source="lines",
        many=True,
        read_only=True,
    )

    events = ShipmentEventSerializer(
        many=True,
        read_only=True,
    )

    transporter_name = serializers.CharField(
        source="transporter.name",
        read_only=True,
    )

    vehicle_registration = serializers.CharField(
        source="vehicle.registration_number",
        read_only=True,
    )

    transfer_number = serializers.CharField(
        source="transfer.transfer_number",
        read_only=True,
    )

    class Meta:
        model = Shipment

        fields = [
            "id",
            "shipment_number",
            "transfer",
            "transfer_number",
            "transporter",
            "transporter_name",
            "vehicle",
            "vehicle_registration",
            "driver_name",
            "driver_phone",
            "status",
            "origin_address",
            "destination_address",
            "planned_dispatch_at",
            "dispatched_at",
            "estimated_delivery_at",
            "arrived_at",
            "delivered_at",
            "distance_km",
            "transport_cost",
            "currency_code",
            "tracking_reference",
            "dispatch_reference",
            "delivery_reference",
            "dispatch_notes",
            "delivery_notes",
            "created_by",
            "created_at",
            "updated_at",
            "shipment_lines",
            "events",
        ]

        read_only_fields = fields


class ShipmentCreateSerializer(serializers.Serializer):

    transfer_id = serializers.UUIDField()

    transporter_id = serializers.UUIDField()

    vehicle_id = serializers.UUIDField()

    driver_name = serializers.CharField(
        max_length=150,
    )

    driver_phone = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    planned_dispatch_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    estimated_delivery_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    distance_km = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0,
        required=False,
        allow_null=True,
    )

    transport_cost = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

    currency_code = serializers.CharField(
        max_length=3,
        required=False,
        allow_blank=True,
    )


class ShipmentTrackingSerializer(serializers.Serializer):

    event_type = serializers.ChoiceField(
        choices=[
            "PICKED_UP",
            "IN_TRANSIT",
            "LOCATION_UPDATE",
            "ARRIVED",
        ]
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=False,
        allow_null=True,
    )

    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=False,
        allow_null=True,
    )


class ShipmentDelaySerializer(serializers.Serializer):

    description = serializers.CharField(
        min_length=5,
    )


class ShipmentExceptionCreateSerializer(serializers.Serializer):

    exception_type = serializers.ChoiceField(
        choices=[
            "DELAY",
            "DAMAGE",
            "LOSS",
            "TEMPERATURE",
            "VEHICLE_BREAKDOWN",
            "ROUTE_DISRUPTION",
            "OTHER",
        ]
    )

    description = serializers.CharField(
        min_length=5,
    )


class ShipmentExceptionResolveSerializer(serializers.Serializer):

    resolution_notes = serializers.CharField(
        min_length=5,
    )


class ShipmentDeliverySerializer(serializers.Serializer):

    delivery_reference = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    delivery_notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class ShipmentDispatchSerializer(serializers.Serializer):

    dispatch_reference = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    dispatch_notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )