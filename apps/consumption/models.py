import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ConsumptionRecordStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class ConsumptionSource(models.TextChoices):
    DISPENSING = "DISPENSING", "Patient dispensing"
    CLINICAL_USE = "CLINICAL_USE", "Clinical use"
    PROGRAMMATIC = "PROGRAMMATIC", "Programmatic use"
    OTHER = "OTHER", "Other"


class ConsumptionReportingMethod(models.TextChoices):
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"
    MONTHLY = "MONTHLY", "Monthly"


class ConsumptionAnomalyType(models.TextChoices):
    HIGH_CONSUMPTION = "HIGH_CONSUMPTION", "Unusually high consumption"
    LOW_CONSUMPTION = "LOW_CONSUMPTION", "Unusually low consumption"
    ZERO_CONSUMPTION = "ZERO_CONSUMPTION", "Zero consumption"
    DATA_GAP = "DATA_GAP", "Missing consumption report"
    SUDDEN_CHANGE = "SUDDEN_CHANGE", "Sudden consumption change"
    DUPLICATE = "DUPLICATE", "Possible duplicate record"


class DailyConsumption(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="daily_consumption_records",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="daily_consumption_records",
    )

    batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
        related_name="daily_consumption_records",
        null=True,
        blank=True,
    )

    consumption_date = models.DateField()

    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
    )

    unit_code = models.CharField(
        max_length=30,
        help_text="The unit used for this consumption quantity.",
    )

    source = models.CharField(
        max_length=20,
        choices=ConsumptionSource.choices,
        default=ConsumptionSource.DISPENSING,
    )

    reporting_method = models.CharField(
        max_length=20,
        choices=ConsumptionReportingMethod.choices,
        default=ConsumptionReportingMethod.DAILY,
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(blank=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_daily_consumption",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-consumption_date", "medicine__generic_name"]
        indexes = [
            models.Index(
                fields=["facility", "consumption_date"],
            ),
            models.Index(
                fields=["medicine", "consumption_date"],
            ),
            models.Index(
                fields=["facility", "medicine", "consumption_date"],
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="daily_consumption_quantity_nonnegative",
            ),
        ]

    def clean(self):
        if self.batch_id and self.medicine_id:
            if self.batch.medicine_id != self.medicine_id:
                raise ValidationError(
                    "The selected batch does not belong to this medicine."
                )

        if self.batch_id and self.facility_id:
            # A batch must belong to a warehouse associated with
            # the facility's organization.
            if self.batch.warehouse.organization_id != self.facility.organization_id:
                raise ValidationError(
                    "The batch warehouse is outside the facility organization."
                )

        if self.quantity is not None and self.quantity < 0:
            raise ValidationError("Consumption quantity cannot be negative.")

        if self.unit_code:
            self.unit_code = self.unit_code.strip().upper()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.facility.name} - "
            f"{self.medicine.generic_name} - "
            f"{self.consumption_date}"
        )


class MonthlyConsumptionReport(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="monthly_consumption_reports",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="monthly_consumption_reports",
    )

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()

    opening_balance = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    received_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    consumed_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    losses_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    closing_balance = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=0,
    )

    stockout_days = models.PositiveSmallIntegerField(default=0)

    reporting_unit = models.CharField(max_length=30)

    status = models.CharField(
        max_length=20,
        choices=ConsumptionRecordStatus.choices,
        default=ConsumptionRecordStatus.DRAFT,
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_monthly_consumption_reports",
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_monthly_consumption_reports",
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "medicine", "year", "month"],
                name="uniq_facility_medicine_monthly_report",
            ),
            models.CheckConstraint(
                condition=Q(month__gte=1) & Q(month__lte=12),
                name="monthly_consumption_valid_month",
            ),
            models.CheckConstraint(
                condition=Q(year__gte=2000) & Q(year__lte=2100),
                name="monthly_consumption_valid_year",
            ),
            models.CheckConstraint(
                condition=Q(opening_balance__gte=0),
                name="monthly_consumption_opening_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(received_quantity__gte=0),
                name="monthly_consumption_received_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(consumed_quantity__gte=0),
                name="monthly_consumption_consumed_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(losses_quantity__gte=0),
                name="monthly_consumption_losses_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(closing_balance__gte=0),
                name="monthly_consumption_closing_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=["facility", "year", "month"]),
            models.Index(fields=["medicine", "year", "month"]),
            models.Index(fields=["status", "year", "month"]),
        ]

    def clean(self):
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValidationError("Month must be between 1 and 12.")

        if self.stockout_days > 31:
            raise ValidationError("Stockout days cannot exceed 31.")

        if self.year is not None and not 2000 <= self.year <= 2100:
            raise ValidationError("Year must be between 2000 and 2100.")

        if self.status == ConsumptionRecordStatus.APPROVED:
            if not self.approved_by_id or not self.approved_at:
                raise ValidationError(
                    "Approved reports require an approver and approval date."
                )

        if self.status == ConsumptionRecordStatus.SUBMITTED:
            if not self.submitted_by_id or not self.submitted_at:
                raise ValidationError(
                    "Submitted reports require a submitter and submission date."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.facility.name} - "
            f"{self.medicine.generic_name} - "
            f"{self.year}-{self.month:02d}"
        )


class ConsumptionAnomaly(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="consumption_anomalies",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="consumption_anomalies",
    )

    anomaly_type = models.CharField(
        max_length=30,
        choices=ConsumptionAnomalyType.choices,
    )

    reporting_period_start = models.DateField()
    reporting_period_end = models.DateField()

    observed_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        null=True,
        blank=True,
    )

    expected_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        null=True,
        blank=True,
    )

    description = models.TextField()

    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["facility", "is_resolved"]),
            models.Index(fields=["medicine", "anomaly_type"]),
            models.Index(fields=["reporting_period_start"]),
        ]

    def clean(self):
        if (
            self.reporting_period_start
            and self.reporting_period_end
            and self.reporting_period_end < self.reporting_period_start
        ):
            raise ValidationError("Reporting period end cannot precede its start.")

        if self.is_resolved and not self.resolved_at:
            raise ValidationError("Resolved anomalies require a resolution date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.anomaly_type} - "
            f"{self.facility.name} - "
            f"{self.medicine.generic_name}"
        )
