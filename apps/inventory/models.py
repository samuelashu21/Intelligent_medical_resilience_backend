import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StockStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    QUARANTINED = "QUARANTINED", "Quarantined"
    DAMAGED = "DAMAGED", "Damaged"
    EXPIRED = "EXPIRED", "Expired"
    BLOCKED = "BLOCKED", "Blocked"


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
        choices=StockStatus.choices,
        default=StockStatus.AVAILABLE,
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
                condition=(
                    Q(unit_cost__isnull=True)
                    | Q(unit_cost__gte=0)
                ),
                name="stock_batch_cost_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.manufacture_date
            and self.manufacture_date > self.expiry_date
        ):
            raise ValidationError({
                "manufacture_date": (
                    "Manufacture date cannot be after expiry date."
                )
            })

        if self.location_id and self.warehouse_id:
            if self.location.zone.warehouse_id != self.warehouse_id:
                raise ValidationError({
                    "location": (
                        "The storage location must belong to this warehouse."
                    )
                })

        if self.presentation_id and self.medicine_id:
            if self.presentation.medicine_id != self.medicine_id:
                raise ValidationError({
                    "presentation": (
                        "The presentation must belong to this medicine."
                    )
                })

        if self.supplier_id and not self.supplier.is_active:
            raise ValidationError({
                "supplier": "Inactive suppliers cannot be used for new batches."
            })

        if self.expiry_date < self.received_date:
            raise ValidationError({
                "expiry_date": "An expired batch cannot be newly received."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.expiry_date < timezone.localdate()

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.localdate()).days

    def __str__(self):
        return f"{self.medicine} - {self.batch_number}"


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
                condition=Q(
                    quantity_reserved__lte=models.F("quantity_on_hand")
                ),
                name="inventory_reserved_lte_on_hand",
            ),
        ]

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved

    def __str__(self):
        return (
            f"{self.batch.batch_number}: "
            f"{self.quantity_on_hand}"
        )


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
            raise ValidationError(
                "Existing stock movements cannot be updated."
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Stock movements cannot be deleted."
        )

    def __str__(self):
        return (
            f"{self.movement_type}: "
            f"{self.batch.batch_number} ({self.quantity})"
        )


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
        return f"{self.reference_number} - {self.quantity}"