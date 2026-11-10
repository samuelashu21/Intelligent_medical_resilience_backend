import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TransferStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    IN_APPROVAL = "IN_APPROVAL", "In Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    RESERVED = "RESERVED", "Stock Reserved"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH", "Ready for Dispatch"
    DISPATCHED = "DISPATCHED", "Dispatched"
    RECEIVED = "RECEIVED", "Received"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class TransferPriority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class TransferSource(models.TextChoices):
    OPTIMIZATION = "OPTIMIZATION", "Optimization"
    RECOMMENDATION = "RECOMMENDATION", "Recommendation"
    MANUAL = "MANUAL", "Manual"


class TransferApprovalDecisionType(models.TextChoices):
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class TransferRequest(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transfer_number = models.CharField(
        max_length=60,
        unique=True,
        editable=False,
    )

    source = models.CharField(
        max_length=20,
        choices=TransferSource.choices,
        default=TransferSource.MANUAL,
    )

    optimization_run = models.ForeignKey(
        "redistribution.RedistributionOptimizationRun",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transfer_requests",
    )

    donor_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="outgoing_transfer_requests",
    )

    recipient_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="incoming_transfer_requests",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="transfer_requests",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_transfer_requests",
    )

    priority = models.CharField(
        max_length=20,
        choices=TransferPriority.choices,
        default=TransferPriority.NORMAL,
    )

    status = models.CharField(
        max_length=30,
        choices=TransferStatus.choices,
        default=TransferStatus.DRAFT,
    )

    justification = models.TextField()

    rejection_reason = models.TextField(blank=True)

    cancellation_reason = models.TextField(blank=True)

    current_approval_level = models.PositiveIntegerField(
        default=1,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reserved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "priority", "created_at"]
            ),
            models.Index(
                fields=["donor_facility", "status"]
            ),
            models.Index(
                fields=["recipient_facility", "status"]
            ),
        ]

    def save(self, *args, **kwargs):

        if not self.transfer_number:
            self.transfer_number = (
                f"TR-{timezone.now():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)

    def clean(self):

        if (
            self.donor_facility_id
            and self.recipient_facility_id
            and self.donor_facility_id == self.recipient_facility_id
        ):
            raise ValidationError(
                "Donor and recipient facilities must be different."
            )

        if self.source == TransferSource.OPTIMIZATION:
            if not self.optimization_run_id:
                raise ValidationError(
                    "Optimization run is required for optimization transfers."
                )

        if (
            self.optimization_run_id
            and self.optimization_run.status != "COMPLETED"
        ):
            raise ValidationError(
                "Transfers can only be created from completed optimization runs."
            )

    def __str__(self):
        return self.transfer_number


class TransferRequestLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transfer = models.ForeignKey(
        TransferRequest,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    optimization_allocation = models.ForeignKey(
        "redistribution.RedistributionOptimizationAllocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transfer_lines",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
    )

    batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
    )

    requested_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    approved_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
    )

    reserved_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    unit_code = models.CharField(
        max_length=30,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(requested_quantity__gt=0),
                name="transfer_line_requested_positive",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__gte=0),
                name="transfer_line_reserved_nonnegative",
            ),
        ]

    def clean(self):

        if self.requested_quantity <= 0:
            raise ValidationError(
                "Requested quantity must be positive."
            )

        if (
            self.approved_quantity is not None
            and self.approved_quantity < 0
        ):
            raise ValidationError(
                "Approved quantity cannot be negative."
            )

        if (
            self.approved_quantity is not None
            and self.approved_quantity > self.requested_quantity
        ):
            raise ValidationError(
                "Approved quantity cannot exceed requested quantity."
            )

        if self.reserved_quantity > (
            self.approved_quantity or 0
        ):
            raise ValidationError(
                "Reserved quantity cannot exceed approved quantity."
            )

        if self.batch_id and self.medicine_id:
            if self.batch.medicine_id != self.medicine_id:
                raise ValidationError(
                    "The batch does not belong to this medicine."
                )

    def __str__(self):
        return (
            f"{self.transfer.transfer_number} - "
            f"{self.medicine}"
        )


class TransferApprovalStage(models.Model):
    """
    Configurable approval stage for a transfer policy.

    A policy can require one or multiple sequential stages.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="transfer_approval_stages",
    )

    level = models.PositiveIntegerField()

    name = models.CharField(
        max_length=120,
    )

    required_role_code = models.CharField(
        max_length=80,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["level"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "level"],
                condition=Q(is_active=True),
                name="unique_active_transfer_stage_level",
            ),
        ]

    def __str__(self):
        return f"{self.organization} - {self.name}"


class TransferApprovalDecision(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transfer = models.ForeignKey(
        TransferRequest,
        on_delete=models.CASCADE,
        related_name="approval_decisions",
    )

    stage = models.ForeignKey(
        TransferApprovalStage,
        on_delete=models.PROTECT,
        related_name="decisions",
    )

    decision = models.CharField(
        max_length=20,
        choices=TransferApprovalDecisionType.choices,
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transfer_approval_decisions",
    )

    comments = models.TextField(blank=True)

    decided_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["stage__level", "decided_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "stage"],
                name="unique_transfer_decision_per_stage",
            ),
        ]

    def __str__(self):
        return (
            f"{self.transfer.transfer_number} - "
            f"{self.stage.name} - {self.decision}"
        )