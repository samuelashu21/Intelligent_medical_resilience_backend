
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone


# ==========================================================
# RECEIVING STATUS
# ==========================================================

class ReceivingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    POSTED = "POSTED", "Posted"


# ==========================================================
# DISCREPANCY TYPES
# ==========================================================

class DiscrepancyType(models.TextChoices):
    MISSING = "MISSING", "Missing"
    DAMAGED = "DAMAGED", "Damaged"
    EXPIRED = "EXPIRED", "Expired"
    EXCESS = "EXCESS", "Excess"
    OTHER = "OTHER", "Other"


# ==========================================================
# DISCREPANCY STATUS
# ==========================================================

class DiscrepancyStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    RESOLVED = "RESOLVED", "Resolved"


# ==========================================================
# RECEIVING RECORD MODEL
# ==========================================================

class ReceivingRecord(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    receipt_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )

    shipment = models.OneToOneField(
        "logistics.Shipment",
        on_delete=models.PROTECT,
        related_name="receiving_record",
    )

    recipient_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="receiving_records",
    )

    receiving_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="receiving_records",
    )

    status = models.CharField(
        max_length=20,
        choices=ReceivingStatus.choices,
        default=ReceivingStatus.DRAFT,
        db_index=True,
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_receiving_records",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submitted_receiving_records",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_receiving_records",
    )

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="posted_receiving_records",
    )

    received_at = models.DateTimeField(
        default=timezone.now,
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

    rejection_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["recipient_facility", "status"],
            ),
            models.Index(
                fields=["receiving_warehouse", "received_at"],
            ),
        ]

    def save(self, *args, **kwargs):

        if not self.receipt_number:
            date_part = timezone.localdate().strftime("%Y%m%d")

            self.receipt_number = (
                f"RCV-{date_part}-{uuid.uuid4().hex[:8].upper()}"
            )

        super().save(*args, **kwargs)

    def clean(self):

        if (
            self.receiving_warehouse_id
            and self.recipient_facility_id
        ):
            warehouse_facility_id = getattr(
                self.receiving_warehouse,
                "facility_id",
                None,
            )

            if warehouse_facility_id != self.recipient_facility_id:
                raise ValidationError({
                    "receiving_warehouse": (
                        "The receiving warehouse must belong "
                        "to the recipient facility."
                    )
                })

        if self.shipment_id and self.recipient_facility_id:

            shipment_recipient_id = (
                self.shipment.transfer.recipient_facility_id
            )

            if shipment_recipient_id != self.recipient_facility_id:
                raise ValidationError({
                    "recipient_facility": (
                        "The receiving facility must match "
                        "the shipment destination."
                    )
                })

    # ------------------------------------------------------
    # RECEIVING DISCREPANCIES
    # ------------------------------------------------------

    @property
    def discrepancies(self):
        return ReceivingDiscrepancy.objects.filter(
            receiving_line__receiving_record=self
        )

    def __str__(self):
        return self.receipt_number


# ==========================================================
# RECEIVING LINE MODEL
# ==========================================================

class ReceivingLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    receiving_record = models.ForeignKey(
        ReceivingRecord,
        on_delete=models.PROTECT,
        related_name="lines",
    )

    shipment_line = models.OneToOneField(
        "logistics.ShipmentLine",
        on_delete=models.PROTECT,
        related_name="receiving_line",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="receiving_lines",
    )

    batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
        related_name="receiving_lines",
    )

    dispatched_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    physically_received_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    accepted_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    damaged_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    expired_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    other_rejected_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    unit_code = models.CharField(max_length=30)

    inspection_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(dispatched_quantity__gt=0),
                name="receiving_line_dispatched_positive",
            ),
            models.CheckConstraint(
                condition=Q(physically_received_quantity__gte=0),
                name="receiving_line_physical_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(accepted_quantity__gte=0),
                name="receiving_line_accepted_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(damaged_quantity__gte=0),
                name="receiving_line_damaged_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(expired_quantity__gte=0),
                name="receiving_line_expired_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(other_rejected_quantity__gte=0),
                name="receiving_line_other_rejected_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(
                    accepted_quantity__lte=F(
                        "physically_received_quantity"
                    )
                ),
                name="receiving_line_accepted_not_above_received",
            ),
            models.CheckConstraint(
                condition=Q(
                    accepted_quantity__lte=F(
                        "dispatched_quantity"
                    )
                ),
                name="receiving_line_accepted_not_above_dispatched",
            ),
        ]

    # ------------------------------------------------------
    # QUANTITY CALCULATIONS
    # ------------------------------------------------------

    @property
    def missing_quantity(self):
        return max(
            self.dispatched_quantity
            - self.physically_received_quantity,
            0,
        )

    @property
    def excess_quantity(self):
        return max(
            self.physically_received_quantity
            - self.dispatched_quantity,
            0,
        )

    @property
    def rejected_quantity(self):
        return (
            self.physically_received_quantity
            - self.accepted_quantity
        )

    @property
    def unexplained_rejected_quantity(self):
        categorized = (
            self.damaged_quantity
            + self.expired_quantity
            + self.other_rejected_quantity
        )

        return max(
            self.rejected_quantity - categorized,
            0,
        )

    # ------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------

    def clean(self):

        if self.shipment_line_id:

            if self.medicine_id != self.shipment_line.medicine_id:
                raise ValidationError(
                    "Medicine must match the shipment line."
                )

            if self.batch_id != self.shipment_line.batch_id:
                raise ValidationError(
                    "Batch must match the dispatched shipment batch."
                )

            if (
                self.dispatched_quantity
                != self.shipment_line.dispatched_quantity
            ):
                raise ValidationError(
                    "Dispatched quantity must match the shipment line."
                )

            if self.unit_code != self.shipment_line.unit_code:
                raise ValidationError(
                    "Unit must match the shipment line."
                )

        categorized_rejected = (
            self.damaged_quantity
            + self.expired_quantity
            + self.other_rejected_quantity
        )

        if categorized_rejected > self.rejected_quantity:
            raise ValidationError(
                "Categorized rejected quantity cannot exceed "
                "total rejected quantity."
            )

    def __str__(self):
        return (
            f"{self.receiving_record.receipt_number} - "
            f"{self.medicine}"
        )


# ==========================================================
# RECEIVING DISCREPANCY MODEL
# ==========================================================

class ReceivingDiscrepancy(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    receiving_line = models.ForeignKey(
        ReceivingLine,
        on_delete=models.PROTECT,
        related_name="discrepancies",
    )

    discrepancy_type = models.CharField(
        max_length=20,
        choices=DiscrepancyType.choices,
    )

    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    status = models.CharField(
        max_length=20,
        choices=DiscrepancyStatus.choices,
        default=DiscrepancyStatus.OPEN,
    )

    description = models.TextField()

    resolution_notes = models.TextField(blank=True)

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_receiving_discrepancies",
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_receiving_discrepancies",
    )

    reported_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-reported_at"]

        indexes = [
            models.Index(
                fields=["discrepancy_type", "status"],
            ),
        ]

    def clean(self):

        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError(
                "Discrepancy quantity must be positive."
            )

        if not self.description or not self.description.strip():
            raise ValidationError(
                "A discrepancy description is required."
            )

    def __str__(self):
        return (
            f"{self.discrepancy_type} - "
            f"{self.receiving_line_id}"
        )


# ==========================================================
# TRANSFER RECONCILIATION STATUS
# ==========================================================

class TransferReconciliationStatus(models.TextChoices):
    COMPLETE = "COMPLETE", "Complete"
    PARTIAL = "PARTIAL", "Partial"
    DISCREPANCY = "DISCREPANCY", "Discrepancy"


# ==========================================================
# TRANSFER RECONCILIATION MODEL
# ==========================================================

class TransferReconciliation(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transfer = models.ForeignKey(
        "redistribution.TransferRequest",
        on_delete=models.PROTECT,
        related_name="reconciliations",
    )

    receiving_record = models.OneToOneField(
        ReceivingRecord,
        on_delete=models.PROTECT,
        related_name="reconciliation",
    )

    dispatched_quantity_total = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    physically_received_quantity_total = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    accepted_quantity_total = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    missing_quantity_total = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    excess_quantity_total = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    rejected_quantity_total = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=TransferReconciliationStatus.choices,
        default=TransferReconciliationStatus.PARTIAL,
    )

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    reconciled_at = models.DateTimeField(auto_now_add=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-reconciled_at"]

    def __str__(self):
        return (
            f"Reconciliation {self.transfer_id} - {self.status}"
        )
