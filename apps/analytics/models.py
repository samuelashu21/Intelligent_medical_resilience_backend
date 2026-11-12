import uuid

from django.conf import settings
from django.db import models


class MedicineSupplyChainRisk(models.Model):

    class RiskCategory(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    class ReviewStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        ACTION_PLANNED = "ACTION_PLANNED", "Action planned"
        RESOLVED = "RESOLVED", "Resolved"
        DISMISSED = "DISMISSED", "Dismissed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="supply_chain_risks",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="supply_chain_risks",
    )

    risk_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    risk_category = models.CharField(
        max_length=20,
        choices=RiskCategory.choices,
    )

    component_scores = models.JSONField(default=dict)

    reasons = models.JSONField(default=list)

    recommended_actions = models.JSONField(default=list)

    data_completeness = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=1.0,
    )

    critical_override = models.BooleanField(default=False)

    model_version = models.CharField(max_length=50)

    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.OPEN,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_supply_chain_risks",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    resolution_notes = models.TextField(blank=True)

    detected_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score", "-detected_at"]

        indexes = [
            models.Index(
                fields=["facility", "risk_category"]
            ),
            models.Index(
                fields=["medicine", "risk_category"]
            ),
            models.Index(
                fields=["review_status", "-risk_score"]
            ),
            models.Index(
                fields=["-detected_at"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.facility_id} - "
            f"{self.medicine_id} - "
            f"{self.risk_category}"
        )