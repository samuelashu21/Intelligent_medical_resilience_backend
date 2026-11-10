import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class WarehouseType(models.TextChoices):
    CENTRAL = "CENTRAL", "Central warehouse"
    REGIONAL = "REGIONAL", "Regional warehouse"
    DISTRICT = "DISTRICT", "District warehouse"
    FACILITY = "FACILITY", "Facility warehouse"
    HOSPITAL = "HOSPITAL", "Hospital warehouse"
    PHARMACY = "PHARMACY", "Pharmacy"
    COLD_CHAIN = "COLD_CHAIN", "Cold-chain warehouse"
    OTHER = "OTHER", "Other"


class WarehouseStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    SUSPENDED = "SUSPENDED", "Suspended"
    CLOSED = "CLOSED", "Closed"


class StorageType(models.TextChoices):
    AMBIENT = "AMBIENT", "Ambient"
    REFRIGERATED = "REFRIGERATED", "Refrigerated"
    FROZEN = "FROZEN", "Frozen"
    CONTROLLED = "CONTROLLED", "Controlled storage"
    SECURE = "SECURE", "Secure storage"
    OTHER = "OTHER", "Other"


class Warehouse(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(max_length=255)

    warehouse_type = models.CharField(
        max_length=30,
        choices=WarehouseType.choices,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="warehouses",
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="warehouses",
        null=True,
        blank=True,
    )

    description = models.TextField(blank=True)

    country = models.ForeignKey(
        "medicines.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="warehouses",
    )

    address = models.TextField(blank=True)

    city = models.CharField(max_length=150, blank=True)

    administrative_area = models.CharField(
        max_length=150,
        blank=True,
    )

    postal_code = models.CharField(max_length=30, blank=True)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    phone = models.CharField(max_length=30, blank=True)

    email = models.EmailField(blank=True)

    total_capacity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum usable storage capacity.",
    )

    capacity_unit = models.CharField(
        max_length=30,
        default="CUBIC_METER",
    )

    status = models.CharField(
        max_length=20,
        choices=WarehouseStatus.choices,
        default=WarehouseStatus.DRAFT,
    )

    is_cold_chain_capable = models.BooleanField(default=False)

    has_backup_power = models.BooleanField(default=False)

    has_temperature_monitoring = models.BooleanField(default=False)

    operating_hours = models.JSONField(default=dict, blank=True)

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_warehouses",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="warehouse_org_status_idx",
            ),
            models.Index(
                fields=["warehouse_type", "status"],
                name="warehouse_type_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(Q(total_capacity__isnull=True) | Q(total_capacity__gt=0)),
                name="warehouse_capacity_positive",
            ),
        ]

    def clean(self):
        super().clean()

        self.code = self.code.strip().upper()
        self.name = self.name.strip()

        if self.facility_id:
            if self.facility.organization_id != self.organization_id:
                raise ValidationError(
                    {
                        "facility": (
                            "The facility must belong to the selected organization."
                        )
                    }
                )

        if self.latitude is not None:
            if not -90 <= self.latitude <= 90:
                raise ValidationError(
                    {"latitude": "Latitude must be between -90 and 90."}
                )

        if self.longitude is not None:
            if not -180 <= self.longitude <= 180:
                raise ValidationError(
                    {"longitude": "Longitude must be between -180 and 180."}
                )

        if self.is_cold_chain_capable:
            if not self.has_temperature_monitoring:
                raise ValidationError(
                    {
                        "has_temperature_monitoring": (
                            "Cold-chain warehouses must have temperature "
                            "monitoring configured."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class StorageZone(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="zones",
    )

    code = models.CharField(max_length=50)

    name = models.CharField(max_length=150)

    storage_type = models.CharField(
        max_length=30,
        choices=StorageType.choices,
    )

    description = models.TextField(blank=True)

    capacity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    capacity_unit = models.CharField(
        max_length=30,
        default="CUBIC_METER",
    )

    minimum_temperature = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    maximum_temperature = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    humidity_minimum = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    humidity_maximum = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["warehouse", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "code"],
                name="unique_warehouse_zone_code",
            ),
            models.CheckConstraint(
                condition=(Q(capacity__isnull=True) | Q(capacity__gt=0)),
                name="storage_zone_capacity_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(minimum_temperature__isnull=True)
                    | Q(maximum_temperature__isnull=True)
                    | Q(maximum_temperature__gte=models.F("minimum_temperature"))
                ),
                name="storage_zone_temperature_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(humidity_minimum__isnull=True)
                    | Q(humidity_maximum__isnull=True)
                    | Q(humidity_maximum__gte=models.F("humidity_minimum"))
                ),
                name="storage_zone_humidity_range",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.minimum_temperature is not None
            and self.maximum_temperature is not None
            and self.minimum_temperature > self.maximum_temperature
        ):
            raise ValidationError(
                {
                    "maximum_temperature": (
                        "Maximum temperature cannot be below minimum temperature."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warehouse.code} - {self.code}"


class StorageLocation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    zone = models.ForeignKey(
        StorageZone,
        on_delete=models.PROTECT,
        related_name="locations",
    )

    code = models.CharField(max_length=50)

    name = models.CharField(max_length=150, blank=True)

    aisle = models.CharField(max_length=30, blank=True)

    rack = models.CharField(max_length=30, blank=True)

    shelf = models.CharField(max_length=30, blank=True)

    bin_number = models.CharField(max_length=30, blank=True)

    capacity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    capacity_unit = models.CharField(
        max_length=30,
        default="CUBIC_METER",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["zone", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "code"],
                name="unique_storage_location_code",
            ),
            models.CheckConstraint(
                condition=(Q(capacity__isnull=True) | Q(capacity__gt=0)),
                name="storage_location_capacity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.zone.code} - {self.code}"


class WarehouseManagerAssignment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="manager_assignments",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="warehouse_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouse_manager_assignments_created",
    )

    is_active = models.BooleanField(default=True)

    valid_from = models.DateTimeField(default=timezone.now)

    valid_until = models.DateTimeField(null=True, blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "user"],
                condition=Q(is_active=True),
                name="unique_active_warehouse_manager",
            ),
        ]

    def clean(self):
        super().clean()

        if self.valid_until and self.valid_until <= self.valid_from:
            raise ValidationError(
                {"valid_until": ("Assignment end time must be after start time.")}
            )

        if not self.user.is_active:
            raise ValidationError(
                {"user": "An inactive user cannot manage a warehouse."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.warehouse.code}"


class WarehouseTemperatureReading(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="temperature_readings",
    )

    zone = models.ForeignKey(
        StorageZone,
        on_delete=models.PROTECT,
        related_name="temperature_readings",
        null=True,
        blank=True,
    )

    temperature = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    humidity = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    recorded_at = models.DateTimeField(default=timezone.now)

    source = models.CharField(
        max_length=30,
        choices=[
            ("MANUAL", "Manual"),
            ("SENSOR", "IoT sensor"),
            ("IMPORT", "Imported"),
        ],
        default="MANUAL",
    )

    sensor_identifier = models.CharField(
        max_length=100,
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouse_temperature_readings",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(
                fields=["warehouse", "recorded_at"],
                name="warehouse_temp_time_idx",
            ),
            models.Index(
                fields=["zone", "recorded_at"],
                name="zone_temp_time_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.zone_id and self.zone.warehouse_id != self.warehouse_id:
            raise ValidationError(
                {"zone": "The zone must belong to the selected warehouse."}
            )

        if self.humidity is not None:
            if not 0 <= self.humidity <= 100:
                raise ValidationError(
                    {"humidity": "Humidity must be between 0 and 100."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warehouse.code} - {self.temperature}°C"


class WarehouseCapacitySnapshot(models.Model):
    """
    Periodic capacity observations. This is a foundation for later
    inventory utilization calculations.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="capacity_snapshots",
    )

    measured_at = models.DateTimeField(default=timezone.now)

    used_capacity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    available_capacity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    capacity_unit = models.CharField(
        max_length=30,
        default="CUBIC_METER",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouse_capacity_snapshots",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-measured_at"]
        indexes = [
            models.Index(
                fields=["warehouse", "measured_at"],
                name="warehouse_capacity_time_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.used_capacity < 0 or self.available_capacity < 0:
            raise ValidationError("Capacity values cannot be negative.")

        if self.warehouse.total_capacity is not None:
            total = self.used_capacity + self.available_capacity

            if total > self.warehouse.total_capacity:
                raise ValidationError(
                    "Used plus available capacity exceeds warehouse capacity."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warehouse.code} - {self.measured_at}"
