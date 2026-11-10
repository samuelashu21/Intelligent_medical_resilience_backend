
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# ==========================================================
# TRANSPORTER STATUS
# ==========================================================

class TransporterStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    SUSPENDED = "SUSPENDED", "Suspended"


# ==========================================================
# VEHICLE STATUS
# ==========================================================

class VehicleStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    ASSIGNED = "ASSIGNED", "Assigned"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    INACTIVE = "INACTIVE", "Inactive"


# ==========================================================
# SHIPMENT STATUS
# ==========================================================

class ShipmentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH", "Ready for Dispatch"
    DISPATCHED = "DISPATCHED", "Dispatched"
    IN_TRANSIT = "IN_TRANSIT", "In Transit"
    DELAYED = "DELAYED", "Delayed"
    DELIVERED = "DELIVERED", "Delivered"
    EXCEPTION = "EXCEPTION", "Exception"
    CANCELLED = "CANCELLED", "Cancelled"


# ==========================================================
# SHIPMENT EVENT TYPES
# ==========================================================

class ShipmentEventType(models.TextChoices):
    CREATED = "CREATED", "Created"
    READY = "READY", "Ready for Dispatch"
    DISPATCHED = "DISPATCHED", "Dispatched"
    PICKED_UP = "PICKED_UP", "Picked Up"
    IN_TRANSIT = "IN_TRANSIT", "In Transit"
    LOCATION_UPDATE = "LOCATION_UPDATE", "Location Update"
    DELAYED = "DELAYED", "Delayed"
    ARRIVED = "ARRIVED", "Arrived at Destination"
    DELIVERED = "DELIVERED", "Delivery Reported"
    RECEIVED = "RECEIVED", "Received by recipient"
    EXCEPTION = "EXCEPTION", "Exception"
    CANCELLED = "CANCELLED", "Cancelled"


# ==========================================================
# SHIPMENT EXCEPTION TYPES
# ==========================================================

class ShipmentExceptionType(models.TextChoices):
    DELAY = "DELAY", "Delivery Delay"
    DAMAGE = "DAMAGE", "Medicine Damage"
    LOSS = "LOSS", "Lost Shipment"
    TEMPERATURE = "TEMPERATURE", "Temperature Excursion"
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN", "Vehicle Breakdown"
    ROUTE_DISRUPTION = "ROUTE_DISRUPTION", "Route Disruption"
    OTHER = "OTHER", "Other"


# ==========================================================
# TRANSPORTER MODEL
# ==========================================================

class Transporter(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="transporters",
    )

    code = models.CharField(max_length=50)

    name = models.CharField(max_length=200)

    contact_person = models.CharField(
        max_length=150,
        blank=True,
    )

    phone = models.CharField(
        max_length=40,
        blank=True,
    )

    email = models.EmailField(blank=True)

    address = models.TextField(blank=True)

    license_number = models.CharField(
        max_length=100,
        blank=True,
    )

    license_expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=TransporterStatus.choices,
        default=TransporterStatus.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_transporter_code_per_org",
            ),
        ]

    def __str__(self):
        return self.name


# ==========================================================
# VEHICLE MODEL
# ==========================================================

class Vehicle(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transporter = models.ForeignKey(
        Transporter,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )

    registration_number = models.CharField(
        max_length=60,
        unique=True,
    )

    vehicle_type = models.CharField(
        max_length=100,
    )

    capacity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    capacity_m3 = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    refrigerated = models.BooleanField(default=False)

    temperature_min_c = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    temperature_max_c = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        default=VehicleStatus.AVAILABLE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(capacity_kg__isnull=True)
                    | Q(capacity_kg__gt=0)
                ),
                name="vehicle_capacity_kg_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(capacity_m3__isnull=True)
                    | Q(capacity_m3__gt=0)
                ),
                name="vehicle_capacity_m3_positive",
            ),
        ]

    def clean(self):

        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c > self.temperature_max_c
        ):
            raise ValidationError(
                "Minimum temperature cannot exceed maximum temperature."
            )

        if (
            self.refrigerated
            and (
                self.temperature_min_c is None
                or self.temperature_max_c is None
            )
        ):
            raise ValidationError(
                "Refrigerated vehicles require a configured "
                "temperature range."
            )

    def __str__(self):
        return self.registration_number


# ==========================================================
# SHIPMENT MODEL
# ==========================================================

class Shipment(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    shipment_number = models.CharField(
        max_length=60,
        unique=True,
        editable=False,
    )

    transfer = models.OneToOneField(
        "redistribution.TransferRequest",
        on_delete=models.PROTECT,
        related_name="shipment",
    )

    transporter = models.ForeignKey(
        Transporter,
        on_delete=models.PROTECT,
        related_name="shipments",
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="shipments",
    )

    driver_name = models.CharField(max_length=150)

    driver_phone = models.CharField(
        max_length=40,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.DRAFT,
    )

    origin_address = models.TextField(blank=True)

    destination_address = models.TextField(blank=True)

    planned_dispatch_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    dispatched_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    estimated_delivery_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    distance_km = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    transport_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency_code = models.CharField(
        max_length=3,
        blank=True,
    )

    tracking_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    dispatch_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    delivery_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    dispatch_notes = models.TextField(blank=True)

    delivery_notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shipments",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status", "estimated_delivery_at"]
            ),
            models.Index(
                fields=["transporter", "status"]
            ),
        ]

        constraints = [
            # Only one active shipment per vehicle.
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(
                    status__in=[
                        ShipmentStatus.DRAFT,
                        ShipmentStatus.READY_FOR_DISPATCH,
                        ShipmentStatus.DISPATCHED,
                        ShipmentStatus.IN_TRANSIT,
                        ShipmentStatus.DELAYED,
                        ShipmentStatus.EXCEPTION,
                    ]
                ),
                name="one_active_shipment_per_vehicle",
            ),
        ]

    def save(self, *args, **kwargs):

        if not self.shipment_number:
            self.shipment_number = (
                f"SHP-{timezone.now():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)

    def clean(self):

        if self.transporter_id and self.vehicle_id:
            if self.vehicle.transporter_id != self.transporter_id:
                raise ValidationError(
                    "The vehicle does not belong to this transporter."
                )

        if (
            self.distance_km is not None
            and self.distance_km < 0
        ):
            raise ValidationError(
                "Distance cannot be negative."
            )

        if (
            self.transport_cost is not None
            and self.transport_cost < 0
        ):
            raise ValidationError(
                "Transport cost cannot be negative."
            )

        if (
            self.estimated_delivery_at
            and self.planned_dispatch_at
            and self.estimated_delivery_at < self.planned_dispatch_at
        ):
            raise ValidationError(
                "Estimated delivery cannot precede planned dispatch."
            )

    def __str__(self):
        return self.shipment_number


# ==========================================================
# SHIPMENT LINE MODEL
# ==========================================================

class ShipmentLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    transfer_line = models.OneToOneField(
        "redistribution.TransferRequestLine",
        on_delete=models.PROTECT,
        related_name="shipment_line",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
    )

    batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
    )

    dispatched_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    unit_code = models.CharField(max_length=30)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(dispatched_quantity__gt=0),
                name="shipment_line_dispatched_positive",
            ),
        ]

    def clean(self):

        if self.transfer_line_id:

            if (
                self.transfer_line.batch_id
                != self.batch_id
            ):
                raise ValidationError(
                    "Shipment batch must match transfer line batch."
                )

            if (
                self.transfer_line.medicine_id
                != self.medicine_id
            ):
                raise ValidationError(
                    "Shipment medicine must match transfer line medicine."
                )

            if (
                self.transfer_line.reserved_quantity
                < self.dispatched_quantity
            ):
                raise ValidationError(
                    "Dispatched quantity exceeds reserved quantity."
                )


# ==========================================================
# SHIPMENT EVENT MODEL
# ==========================================================

class ShipmentEvent(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=30,
        choices=ShipmentEventType.choices,
    )

    description = models.TextField(blank=True)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shipment_events",
    )

    event_time = models.DateTimeField(
        default=timezone.now,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event_time", "created_at"]

        indexes = [
            models.Index(
                fields=["shipment", "event_time"]
            ),
        ]

    def clean(self):

        if (
            self.latitude is not None
            and not DecimalRange(-90, 90, self.latitude)
        ):
            raise ValidationError("Invalid latitude.")

        if (
            self.longitude is not None
            and not DecimalRange(-180, 180, self.longitude)
        ):
            raise ValidationError("Invalid longitude.")


# ==========================================================
# DECIMAL RANGE VALIDATION
# ==========================================================

def DecimalRange(minimum, maximum, value):
    return minimum <= value <= maximum


# ==========================================================
# SHIPMENT DOCUMENT MODEL
# ==========================================================

class ShipmentDocument(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_type = models.CharField(
        max_length=40,
        choices=[
            ("DISPATCH_NOTE", "Dispatch Note"),
            ("WAYBILL", "Waybill"),
            ("DELIVERY_PROOF", "Proof of Delivery"),
            ("OTHER", "Other"),
        ],
    )

    file = models.FileField(
        upload_to="logistics/shipments/%Y/%m/",
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    description = models.TextField(blank=True)


# ==========================================================
# SHIPMENT EXCEPTION MODEL
# ==========================================================

class ShipmentException(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.PROTECT,
        related_name="exceptions",
    )

    exception_type = models.CharField(
        max_length=30,
        choices=ShipmentExceptionType.choices,
    )

    description = models.TextField()

    resolved = models.BooleanField(default=False)

    resolution_notes = models.TextField(blank=True)

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_shipment_exceptions",
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_shipment_exceptions",
    )

    reported_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-reported_at"]
