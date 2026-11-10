import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models import F
from django.utils import timezone


class ReplenishmentRequest(models.Model):

    class Status(models.TextChoices):
     DRAFT = "DRAFT", "Draft"
     SUBMITTED = "SUBMITTED", "Submitted"
     APPROVED = "APPROVED", "Approved"
     REJECTED = "REJECTED", "Rejected"
     CANCELLED = "CANCELLED", "Cancelled"
     REVISION_REQUESTED = (
        "REVISION_REQUESTED",
        "Revision Requested",
    )

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        POLICY = "POLICY", "Stock policy"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    request_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="replenishment_requests",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="replenishment_requests",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_replenishment_requests",
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    justification = models.TextField()

    requested_at = models.DateTimeField(
        default=timezone.now,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_replenishment_requests",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_replenishment_requests",
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_replenishment_requests",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-requested_at"]

        indexes = [
            models.Index(
                fields=["facility", "status"],
                name="replen_req_fac_status_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="replen_req_org_status_idx",
            ),
            models.Index(
                fields=["priority", "status"],
                name="replen_req_priority_idx",
            ),
            models.Index(
                fields=["requested_at"],
                name="replen_req_date_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(priority__in=[
                    "LOW", "NORMAL", "HIGH", "CRITICAL"
                ]),
                name="replen_req_valid_priority",
            ),
            models.CheckConstraint(
                condition=Q(status__in=[
                    "DRAFT",
                    "SUBMITTED",
                    "APPROVED",
                    "REJECTED",
                    "CANCELLED",
                ]),
                name="replen_req_valid_status",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.facility_id
            and self.organization_id
            and self.facility.organization_id != self.organization_id
        ):
            errors["organization"] = (
                "The organization must own the requesting facility."
            )

        if self.status == self.Status.APPROVED:
            if not self.approved_by_id or not self.approved_at:
                errors["approved_by"] = (
                    "Approved requests require approval metadata."
                )

        if self.status == self.Status.REJECTED:
            if not self.rejected_by_id or not self.rejected_at:
                errors["rejected_by"] = (
                    "Rejected requests require rejection metadata."
                )

            if not self.rejection_reason.strip():
                errors["rejection_reason"] = (
                    "A rejection reason is required."
                )

        if self.status == self.Status.CANCELLED:
            if not self.cancelled_by_id or not self.cancelled_at:
                errors["cancelled_by"] = (
                    "Cancelled requests require cancellation metadata."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = (
                f"MR-{timezone.now():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.request_number


class ReplenishmentRequestLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    request = models.ForeignKey(
        ReplenishmentRequest,
        on_delete=models.PROTECT,
        related_name="items",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="replenishment_request_lines",
    )

    preferred_supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="replenishment_request_lines",
    )

    requested_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    recommended_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    approved_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
    )

    unit_code = models.CharField(
        max_length=30,
    )

    reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["medicine__generic_name"]

        constraints = [
            models.UniqueConstraint(
                fields=["request", "medicine"],
                name="unique_medicine_per_replen_request",
            ),
            models.CheckConstraint(
                condition=Q(requested_quantity__gt=0),
                name="replen_line_requested_positive",
            ),
            models.CheckConstraint(
                condition=Q(recommended_quantity__gte=0),
                name="replen_line_recommended_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(approved_quantity__isnull=True)
                    | Q(approved_quantity__gte=0)
                ),
                name="replen_line_approved_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}

        if self.requested_quantity <= 0:
            errors["requested_quantity"] = (
                "Requested quantity must be greater than zero."
            )

        if self.recommended_quantity < 0:
            errors["recommended_quantity"] = (
                "Recommended quantity cannot be negative."
            )

        if (
            self.approved_quantity is not None
            and self.approved_quantity < 0
        ):
            errors["approved_quantity"] = (
                "Approved quantity cannot be negative."
            )

        if (
            self.request_id
            and self.request.status != ReplenishmentRequest.Status.DRAFT
        ):
            if self.pk is None:
                errors["request"] = (
                    "Items can only be added to draft requests."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.request.request_number} - "
            f"{self.medicine.generic_name}"
        )


class ApprovalWorkflow(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(max_length=150)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="approval_workflows",
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_approval_workflows",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_approval_workflow_name",
            )
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class ApprovalWorkflowStage(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.PROTECT,
        related_name="stages",
    )

    sequence = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=120)

    organization_type_code = models.CharField(
        max_length=50,
        help_text=(
            "Organization unit type code required for this stage."
        ),
    )

    required_role_code = models.CharField(
        max_length=50,
        help_text="RBAC role code required to approve this stage.",
    )

    required_permission_code = models.CharField(
        max_length=100,
        default="replenishment.approve",
    )

    minimum_priority = models.CharField(
        max_length=20,
        choices=ReplenishmentRequest.Priority.choices,
        default=ReplenishmentRequest.Priority.LOW,
    )

    allow_revision = models.BooleanField(default=True)

    allow_partial_approval = models.BooleanField(default=True)

    is_final_stage = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]

        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "sequence"],
                name="unique_workflow_stage_sequence",
            )
        ]

    def __str__(self):
        return (
            f"{self.workflow.name} - "
            f"{self.sequence} - {self.name}"
        )


class ReplenishmentApproval(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REVISION_REQUESTED = (
            "REVISION_REQUESTED",
            "Revision Requested",
        )
        SKIPPED = "SKIPPED", "Skipped"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    request = models.ForeignKey(
        ReplenishmentRequest,
        on_delete=models.PROTECT,
        related_name="approval_stages",
    )

    workflow_stage = models.ForeignKey(
        ApprovalWorkflowStage,
        on_delete=models.PROTECT,
        related_name="request_approvals",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="replenishment_approvals",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    assigned_at = models.DateTimeField(default=timezone.now)

    due_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="replenishment_stage_decisions",
    )

    cycle_number = models.PositiveSmallIntegerField(
    default=1,
     )
    
    escalation_level = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "workflow_stage__sequence",
        ]

        models.UniqueConstraint(
         fields=[
          "request",
          "workflow_stage",
          "cycle_number",
         ],
         name="unique_request_approval_cycle_stage",
         )

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="replen_appr_org_status_idx",
            ),
            models.Index(
                fields=["status", "due_at"],
                name="replen_appr_due_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.request.request_number} - "
            f"{self.workflow_stage.name}"
        )


class ApprovalDecision(models.Model):

    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REVISION_REQUESTED = (
            "REVISION_REQUESTED",
            "Revision Requested",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    approval = models.ForeignKey(
        ReplenishmentApproval,
        on_delete=models.PROTECT,
        related_name="decisions",
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="replenishment_approval_decisions",
    )

    decision = models.CharField(
        max_length=30,
        choices=Decision.choices,
    )

    comments = models.TextField()

    approved_at = models.DateTimeField(
        default=timezone.now,
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["approved_at"]

        indexes = [
            models.Index(
                fields=["decided_by", "approved_at"],
                name="replen_decision_user_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.approval} - "
            f"{self.decision}"
        )

    def save(self, *args, **kwargs):
        if self.pk and ApprovalDecision.objects.filter(
            pk=self.pk
        ).exists():
            raise ValidationError(
                "Approval decisions cannot be modified."
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Approval decisions cannot be deleted."
        )                