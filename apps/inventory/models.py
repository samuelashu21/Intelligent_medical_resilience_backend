import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class BatchStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    QUARANTINED = "QUARANTINED", "Quarantined"
    DAMAGED = "DAMAGED", "Damaged"
    RECALLED = "RECALLED", "Recalled"
    EXPIRED = "EXPIRED", "Expired"
    DISPOSED = "DISPOSED", "Disposed"
    BLOCKED = "BLOCKED", "Blocked"


# Backwards compatibility alias
StockStatus = BatchStatus


class MovementType(models.TextChoices):
    RECEIPT = "RECEIPT", "Receipt"
    ISSUE = "ISSUE", "Issue"
    ADJUSTMENT_IN = "ADJUSTMENT_IN", "Adjustment in"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Adjustment out"
    TRANSFER_IN = "TRANSFER_IN", "Transfer in"
    TRANSFER_OUT = "TRANSFER_OUT", "Transfer out"
    DAMAGE = "DAMAGE", "Damage"
    EXPIRY = "EXPIRY", "Expiry"


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    RELEASED = "RELEASED", "Released"
    FULFILLED = "FULFILLED", "Fulfilled"
    EXPIRED = "EXPIRED", "Expired"


class StockBatch(models.Model):
    """
    A medicine batch stored at a specific warehouse location.

    The same manufacturer's batch can be represented in more than
    one warehouse or storage location.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="stock_batches",
    )

    presentation = models.ForeignKey(
        "medicines.MedicinePresentation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_batches",
    )

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="stock_batches",
    )

    location = models.ForeignKey(
        "warehouses.StorageLocation",
        on_delete=models.PROTECT,
        related_name="stock_batches",
    )

    batch_number = models.CharField(max_length=100)

    manufacture_date = models.DateField(
        null=True,
        blank=True,
    )

    expiry_date = models.DateField()

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_batches",
    )

    supplier_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    received_date = models.DateField(default=timezone.localdate)

    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="USD",
    )

    status = models.CharField(
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.AVAILABLE,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date", "batch_number"]
        indexes = [
            models.Index(
                fields=["medicine", "warehouse"],
                name="batch_med_wh_idx",
            ),
            models.Index(
                fields=["expiry_date", "status"],
                name="batch_expiry_status_idx",
            ),
            models.Index(
                fields=["warehouse", "location"],
                name="batch_wh_location_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "medicine",
                    "presentation",
                    "warehouse",
                    "location",
                    "batch_number",
                ],
                name="unique_stock_batch_location",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=(Q(unit_cost__isnull=True) | Q(unit_cost__gte=0)),
                name="stock_batch_cost_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()

        if self.manufacture_date and self.manufacture_date > self.expiry_date:
            raise ValidationError(
                {"manufacture_date": ("Manufacture date cannot be after expiry date.")}
            )

        if self.location_id and self.warehouse_id:
            if self.location.zone.warehouse_id != self.warehouse_id:
                raise ValidationError(
                    {
                        "location": (
                            "The storage location must belong to this warehouse."
                        )
                    }
                )

        if self.presentation_id and self.medicine_id:
            if self.presentation.medicine_id != self.medicine_id:
                raise ValidationError(
                    {"presentation": ("The presentation must belong to this medicine.")}
                )

        if self.supplier_id and not self.supplier.is_active:
            raise ValidationError(
                {"supplier": ("Inactive suppliers cannot be used for new batches.")}
            )

        # Only validate expiry vs received date on creation.
        if self._state.adding and self.expiry_date < self.received_date:
            raise ValidationError(
                {"expiry_date": ("An expired batch cannot be newly received.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.expiry_date < timezone.localdate()

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def is_usable(self):
        return (
            self.status == BatchStatus.AVAILABLE
            and self.expiry_date >= timezone.localdate()
        )

    @property
    def expiry_category(self):
        days = self.days_until_expiry

        if days < 0:
            return "EXPIRED"

        if days <= 30:
            return "CRITICAL"

        if days <= 60:
            return "HIGH"

        if days <= 90:
            return "WARNING"

        return "NORMAL"

    def __str__(self):
        return f"{self.medicine} {self.batch_number}"


class InventoryBalance(models.Model):
    """
    Current stock balance for one batch at one location.

    Updated only through inventory services.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.OneToOneField(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="balance",
    )

    quantity_on_hand = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    quantity_reserved = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    last_movement_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=0),
                name="inventory_on_hand_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_reserved__gte=0),
                name="inventory_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_reserved__lte=models.F("quantity_on_hand")),
                name="inventory_reserved_lte_on_hand",
            ),
        ]

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved

    def __str__(self):
        return f"{self.batch.batch_number}: " f"{self.quantity_on_hand}"


class StockMovement(models.Model):
    """
    Append-only inventory ledger.

    Do not update or delete movement records. Corrections must be
    represented by compensating movements.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=25,
        choices=MovementType.choices,
    )

    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )

    reference_type = models.CharField(
        max_length=50,
        blank=True,
    )

    source_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_stock_movements",
    )

    destination_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_stock_movements",
    )

    notes = models.TextField(blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )

    occurred_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["batch", "occurred_at"],
                name="movement_batch_time_idx",
            ),
            models.Index(
                fields=["movement_type", "occurred_at"],
                name="movement_type_time_idx",
            ),
            models.Index(
                fields=["reference_type", "reference_number"],
                name="movement_reference_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="stock_movement_quantity_positive",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and StockMovement.objects.filter(pk=self.pk).exists():
            raise ValidationError(
                "Stock movements are immutable. Create a correcting movement."
            )

        if not self._state.adding:
            raise ValidationError("Existing stock movements cannot be updated.")

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Stock movements cannot be deleted.")

    def __str__(self):
        return f"{self.movement_type}: " f"{self.batch.batch_number} ({self.quantity})"


class StockReservation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
    )

    reference_number = models.CharField(
        max_length=100,
    )

    purpose = models.CharField(
        max_length=255,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
    )

    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_reservations",
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["batch", "status"],
                name="reservation_batch_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="reservation_quantity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.reference_number} {self.quantity}"


class BatchLifecycleAction(models.TextChoices):
    QUARANTINED = "QUARANTINED", "Quarantined"
    RELEASED = "RELEASED", "Released from quarantine"
    MARKED_DAMAGED = "MARKED_DAMAGED", "Marked damaged"
    MARKED_RECALLED = "MARKED_RECALLED", "Marked recalled"
    MARKED_EXPIRED = "MARKED_EXPIRED", "Marked expired"
    DISPOSED = "DISPOSED", "Disposed"
    EXPIRY_WARNING = "EXPIRY_WARNING", "Expiry warning"


class BatchLifecycleEvent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="lifecycle_events",
    )

    action = models.CharField(
        max_length=30,
        choices=BatchLifecycleAction.choices,
    )

    previous_status = models.CharField(
        max_length=20,
        blank=True,
    )

    new_status = models.CharField(
        max_length=20,
        blank=True,
    )

    reason = models.TextField()

    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="batch_lifecycle_events",
        null=True,
        blank=True,
    )

    performed_by_label = models.CharField(
        max_length=100,
        default="SYSTEM",
    )

    metadata = models.JSONField(default=dict, blank=True)

    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["batch", "occurred_at"]),
            models.Index(fields=["action", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.batch.batch_number}: {self.action}"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Batch lifecycle events are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Batch lifecycle events cannot be deleted.")


# Define these enums before StockCount and StockCountLine.
class StockCountStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    POSTED = "POSTED", "Posted"
    CANCELLED = "CANCELLED", "Cancelled"


class StockVarianceReason(models.TextChoices):
    DATA_ENTRY_ERROR = "DATA_ENTRY_ERROR", "Data entry error"
    UNRECORDED_RECEIPT = "UNRECORDED_RECEIPT", "Unrecorded receipt"
    UNRECORDED_ISSUE = "UNRECORDED_ISSUE", "Unrecorded issue"
    DAMAGE = "DAMAGE", "Damaged stock"
    LOSS = "LOSS", "Stock loss"
    THEFT = "THEFT", "Suspected theft"
    EXPIRY = "EXPIRY", "Expired stock"
    COUNTING_ERROR = "COUNTING_ERROR", "Counting error"
    OTHER = "OTHER", "Other"


class StockCountMethod(models.TextChoices):
    FULL = "FULL", "Full physical count"
    CYCLE = "CYCLE", "Cycle count"
    SPOT = "SPOT", "Spot check"


class StockCount(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    reference_number = models.CharField(
        max_length=100,
        unique=True,
    )

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="stock_counts",
    )

    count_method = models.CharField(
        max_length=20,
        choices=StockCountMethod.choices,
        default=StockCountMethod.FULL,
    )

    status = models.CharField(
        max_length=20,
        choices=StockCountStatus.choices,
        default=StockCountStatus.DRAFT,
    )

    scheduled_date = models.DateField(
        default=timezone.localdate,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    posted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stock_counts",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_stock_counts",
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_stock_counts",
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["warehouse", "status"]),
            models.Index(fields=["scheduled_date", "status"]),
        ]

    def __str__(self):
        return self.reference_number


class StockCountLine(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    stock_count = models.ForeignKey(
        StockCount,
        on_delete=models.PROTECT,
        related_name="lines",
    )

    batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
        related_name="stock_count_lines",
    )

    system_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    physical_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        null=True,
        blank=True,
    )

    variance = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    reason = models.CharField(
        max_length=30,
        choices=StockVarianceReason.choices,
        blank=True,
    )

    explanation = models.TextField(blank=True)

    counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_count_lines",
        null=True,
        blank=True,
    )

    counted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["batch__batch_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["stock_count", "batch"],
                name="uniq_batch_per_stock_count",
            ),
            models.CheckConstraint(
                condition=Q(system_quantity__gte=0),
                name="stock_count_system_qty_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(physical_quantity__isnull=True)
                | Q(physical_quantity__gte=0),
                name="stock_count_physical_qty_nonnegative",
            ),
        ]

    def clean(self):
        if self.stock_count_id and self.batch_id:
            if self.batch.warehouse_id != self.stock_count.warehouse_id:
                raise ValidationError(
                    "The batch must belong to the stock count warehouse."
                )

        if self.physical_quantity is not None:
            self.variance = self.physical_quantity - self.system_quantity

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.stock_count.reference_number} - " f"{self.batch.batch_number}"


class StockReconciliation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    stock_count = models.ForeignKey(
        StockCount,
        on_delete=models.PROTECT,
        related_name="reconciliations",
    )

    count_line = models.OneToOneField(
        StockCountLine,
        on_delete=models.PROTECT,
        related_name="reconciliation",
    )

    system_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
    )

    physical_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
    )

    variance = models.DecimalField(
        max_digits=16,
        decimal_places=3,
    )

    adjustment_movement = models.ForeignKey(
        "inventory.StockMovement",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reconciliations",
    )

    reason = models.CharField(
        max_length=30,
        choices=StockVarianceReason.choices,
    )

    explanation = models.TextField()

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="posted_reconciliations",
        null=True,
        blank=True,
    )

    posted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stock_count", "created_at"]),
        ]

    def clean(self):
        expected_variance = self.physical_quantity - self.system_quantity

        if self.variance != expected_variance:
            raise ValidationError(
                "Reconciliation variance does not match the quantities."
            )

        if self.count_line_id:
            if self.count_line.stock_count_id != self.stock_count_id:
                raise ValidationError(
                    "The count line must belong to the selected stock count."
                )

    def __str__(self):
        return f"Reconciliation {self.stock_count.reference_number}"


class BatchExpiryAlert(models.Model):
    class AlertLevel(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        WARNING = "WARNING", "Warning"
        EXPIRED = "EXPIRED", "Expired"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="expiry_alerts",
    )

    alert_level = models.CharField(
        max_length=20,
        choices=AlertLevel.choices,
    )

    threshold_days = models.PositiveIntegerField()

    message = models.TextField()

    is_active = models.BooleanField(default=True)

    first_detected_at = models.DateTimeField(
        default=timezone.now,
    )

    last_detected_at = models.DateTimeField(
        default=timezone.now,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-last_detected_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "alert_level"],
                condition=Q(is_active=True),
                name="uniq_active_batch_expiry_alert",
            ),
        ]
        indexes = [
            models.Index(fields=["alert_level", "is_active"]),
            models.Index(fields=["is_active", "last_detected_at"]),
        ]

    def __str__(self):
        return f"{self.batch.batch_number}: {self.alert_level}"


class StockPolicy(models.Model):

    class PolicyLevel(models.TextChoices):
        ORGANIZATION = "ORGANIZATION", "Organization default"
        FACILITY = "FACILITY", "Facility specific"

    class PolicyStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    policy_level = models.CharField(
        max_length=20,
        choices=PolicyLevel.choices,
        default=PolicyLevel.FACILITY,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="stock_policies",
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="stock_policies",
        null=True,
        blank=True,
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="stock_policies",
    )

    minimum_stock = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    maximum_stock = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    safety_stock = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    buffer_stock = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    lead_time_days = models.PositiveIntegerField(
        default=30,
    )

    review_period_days = models.PositiveIntegerField(
        default=30,
    )

    minimum_order_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    is_essential = models.BooleanField(
        default=False,
    )

    status = models.CharField(
        max_length=20,
        choices=PolicyStatus.choices,
        default=PolicyStatus.DRAFT,
    )

    effective_from = models.DateField(
        default=timezone.localdate,
    )

    effective_until = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_stock_policies",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_stock_policies",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "organization__name",
            "medicine__generic_name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["facility", "medicine"],
                condition=Q(facility__isnull=False),
                name="unique_facility_medicine_stock_policy",
            ),
            models.UniqueConstraint(
                fields=["organization", "medicine"],
                condition=Q(facility__isnull=True),
                name="unique_org_default_medicine_stock_policy",
            ),
            models.CheckConstraint(
                condition=Q(minimum_stock__gte=0),
                name="stock_policy_min_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(maximum_stock__gt=0),
                name="stock_policy_max_positive",
            ),
            models.CheckConstraint(
                condition=Q(safety_stock__gte=0),
                name="stock_policy_safety_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(buffer_stock__gte=0),
                name="stock_policy_buffer_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(minimum_order_quantity__gte=0),
                name="stock_policy_moq_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(maximum_stock__gte=models.F("minimum_stock")),
                name="stock_policy_max_gte_min",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="stock_policy_org_status_idx",
            ),
            models.Index(
                fields=["facility", "status"],
                name="stock_policy_fac_status_idx",
            ),
            models.Index(
                fields=["medicine", "status"],
                name="stock_policy_med_status_idx",
            ),
            models.Index(
                fields=["effective_from", "effective_until"],
                name="stock_policy_effective_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if self.policy_level == self.PolicyLevel.FACILITY:
            if not self.facility_id:
                errors["facility"] = "A facility-specific policy requires a facility."

            elif (
                self.organization_id
                and self.facility.organization_id != self.organization_id
            ):
                errors["facility"] = (
                    "The facility must belong to the selected organization."
                )

        elif self.policy_level == self.PolicyLevel.ORGANIZATION:
            if self.facility_id:
                errors["facility"] = (
                    "An organization default policy cannot reference "
                    "a specific facility."
                )

        if self.minimum_stock < 0:
            errors["minimum_stock"] = "Minimum stock cannot be negative."

        if self.maximum_stock <= 0:
            errors["maximum_stock"] = "Maximum stock must be positive."

        if self.maximum_stock < self.minimum_stock:
            errors["maximum_stock"] = (
                "Maximum stock cannot be lower than minimum stock."
            )

        if self.effective_until and (self.effective_until < self.effective_from):
            errors["effective_until"] = "End date cannot be before the start date."

        if self.status == self.PolicyStatus.ACTIVE:
            if self.effective_until and self.effective_until < timezone.localdate():
                errors["status"] = "An expired policy cannot be activated."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medicine} - " f"{self.facility or self.organization}"
