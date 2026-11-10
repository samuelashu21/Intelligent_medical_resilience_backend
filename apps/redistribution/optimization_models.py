
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class OptimizationRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    INFEASIBLE = "INFEASIBLE", "Infeasible"
    FAILED = "FAILED", "Failed"


class OptimizationAllocationStatus(models.TextChoices):
    PROPOSED = "PROPOSED", "Proposed"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class RedistributionTransportProfile(models.Model):
    """
    Converts one inventory unit into a common transport capacity unit.

    Example:
        1 tablet = 0.00002 m3
        1 bottle = 0.00015 m3

    The conversion must match the inventory unit used by the facility.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="transport_profiles",
    )

    inventory_unit_code = models.CharField(
        max_length=30,
    )

    capacity_units_per_inventory_unit = models.DecimalField(
        max_digits=18,
        decimal_places=9,
    )

    is_active = models.BooleanField(
        default=True,
    )

    effective_from = models.DateField(
        default=timezone.localdate,
    )

    effective_until = models.DateField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "medicine",
                    "inventory_unit_code",
                    "effective_from",
                ],
                name="unique_medicine_transport_unit_start",
            ),
            models.CheckConstraint(
                condition=Q(
                    capacity_units_per_inventory_unit__gt=0
                ),
                name="transport_capacity_conversion_positive",
            ),
        ]

    def clean(self):
        if (
            self.effective_until
            and self.effective_until < self.effective_from
        ):
            raise ValidationError(
                "Transport profile end date cannot precede its start date."
            )

    def __str__(self):
        return f"{self.medicine} - {self.inventory_unit_code}"


class RedistributionOptimizationRun(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    run_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=OptimizationRunStatus.choices,
        default=OptimizationRunStatus.PENDING,
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redistribution_optimization_runs",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="redistribution_optimization_runs",
    )

    objective_value = models.BigIntegerField(
        null=True,
        blank=True,
    )

    solver_status = models.CharField(
        max_length=40,
        blank=True,
    )

    solver_runtime_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
    )

    total_allocated_capacity_units = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0,
    )

    total_unmet_shortage_units = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    total_distance_km = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    total_estimated_transport_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    input_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    solver_metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    algorithm_version = models.CharField(
        max_length=30,
        default="ortools-cp-sat-v1",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):

        if not self.run_number:
            self.run_number = (
                f"OPT-{timezone.now():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.run_number


class RedistributionOptimizationAllocation(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    optimization_run = models.ForeignKey(
        RedistributionOptimizationRun,
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
    )

    donor_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="optimized_outgoing_allocations",
    )

    recipient_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="optimized_incoming_allocations",
    )

    batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
    )

    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    unit_code = models.CharField(
        max_length=30,
    )

    transport_capacity_units = models.DecimalField(
        max_digits=18,
        decimal_places=6,
    )

    distance_km = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    estimated_transport_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=OptimizationAllocationStatus.choices,
        default=OptimizationAllocationStatus.PROPOSED,
    )

    explanation = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["optimization_run", "status"],
            ),
            models.Index(
                fields=["donor_facility", "medicine"],
            ),
            models.Index(
                fields=["recipient_facility", "medicine"],
            ),
        ]

        constraints = [
            # Allocation quantity must be positive.
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="optimization_allocation_positive_qty",
            ),

            # Donor and recipient must be different facilities.
            # Enforced directly by the database.
            models.CheckConstraint(
                condition=~Q(
                    donor_facility=F("recipient_facility")
                ),
                name="optimization_allocation_different_facilities",
            ),
        ]

    def clean(self):

        if (
            self.donor_facility_id
            and self.recipient_facility_id
            and self.donor_facility_id == self.recipient_facility_id
        ):
            raise ValidationError(
                "Donor and recipient must be different."
            )

        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError(
                "Allocation quantity must be positive."
            )

    def __str__(self):
        return (
            f"{self.optimization_run.run_number} - "
            f"{self.medicine}"
        )
