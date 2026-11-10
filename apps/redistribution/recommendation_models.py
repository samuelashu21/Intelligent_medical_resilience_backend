import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

# ============================================================
# RECOMMENDATION STATUS
# ============================================================


class RecommendationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    DEFERRED = "DEFERRED", "Deferred"
    EXPIRED = "EXPIRED", "Expired"


# ============================================================
# RECOMMENDATION PRIORITY
# ============================================================


class RecommendationPriority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


# ============================================================
# REDISTRIBUTION RECOMMENDATION MODEL
# ============================================================


class RedistributionRecommendation(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    recommendation_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="redistribution_recommendations",
    )

    donor_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="outgoing_recommendations",
    )

    recipient_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="incoming_recommendations",
    )

    donor_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="donor_recommendations",
    )

    recipient_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="recipient_recommendations",
    )

    recommended_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    unit_code = models.CharField(
        max_length=30,
    )

    donor_available_before = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    recipient_available_before = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    donor_available_after = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    recipient_available_after = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    donor_coverage_days_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    recipient_coverage_days_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    donor_coverage_days_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    recipient_coverage_days_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=RecommendationPriority.choices,
        default=RecommendationPriority.NORMAL,
    )

    status = models.CharField(
        max_length=20,
        choices=RecommendationStatus.choices,
        default=RecommendationStatus.PENDING,
    )

    priority_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    explanation = models.JSONField(
        default=dict,
        blank=True,
    )

    algorithm_version = models.CharField(
        max_length=30,
        default="redistribution-v1",
    )

    generated_at = models.DateTimeField(
        default=timezone.now,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_redistribution_recommendations",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    review_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ========================================================
    # MODEL CONFIGURATION
    # ========================================================

    class Meta:

        ordering = [
            "-priority_score",
            "-generated_at",
        ]

        indexes = [
            models.Index(
                fields=["status", "priority"],
            ),
            models.Index(
                fields=["medicine", "status"],
            ),
            models.Index(
                fields=["donor_facility", "status"],
            ),
            models.Index(
                fields=["recipient_facility", "status"],
            ),
            models.Index(
                fields=["generated_at"],
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(recommended_quantity__gt=0),
                name="redistribution_recommendation_positive_qty",
            ),
            # Donor and recipient must be different facilities.
            models.CheckConstraint(
                condition=~Q(donor_facility=F("recipient_facility")),
                name="redistribution_different_facilities",
            ),
            models.CheckConstraint(
                condition=Q(priority_score__gte=0),
                name="redistribution_score_nonnegative",
            ),
        ]

    # ========================================================
    # MODEL VALIDATION
    # ========================================================

    def clean(self):

        super().clean()

        # ----------------------------------------------------
        # Validate donor and recipient facilities
        # ----------------------------------------------------

        if (
            self.donor_facility_id
            and self.recipient_facility_id
            and self.donor_facility_id == self.recipient_facility_id
        ):
            raise ValidationError(
                {
                    "recipient_facility": (
                        "Donor and recipient facilities must be different."
                    )
                }
            )

        # ----------------------------------------------------
        # Validate donor organization
        # ----------------------------------------------------

        if (
            self.donor_organization_id
            and self.donor_facility_id
            and self.donor_facility.organization_id != self.donor_organization_id
        ):
            raise ValidationError(
                {
                    "donor_organization": (
                        "Donor organization does not match donor facility."
                    )
                }
            )

        # ----------------------------------------------------
        # Validate recipient organization
        # ----------------------------------------------------

        if (
            self.recipient_organization_id
            and self.recipient_facility_id
            and self.recipient_facility.organization_id
            != self.recipient_organization_id
        ):
            raise ValidationError(
                {
                    "recipient_organization": (
                        "Recipient organization does not match recipient facility."
                    )
                }
            )

        # ----------------------------------------------------
        # Validate recommended quantity
        # ----------------------------------------------------

        if self.recommended_quantity is not None and self.recommended_quantity <= 0:
            raise ValidationError(
                {"recommended_quantity": ("Recommended quantity must be positive.")}
            )

        # ----------------------------------------------------
        # Validate recommendation expiry
        # ----------------------------------------------------

        if (
            self.expires_at
            and self.generated_at
            and self.expires_at <= self.generated_at
        ):
            raise ValidationError(
                {"expires_at": ("Recommendation expiry must be after generation.")}
            )

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        if not self.recommendation_number:
            self.recommendation_number = (
                f"RR-{timezone.now():%Y%m%d}-" f"{uuid.uuid4().hex[:10].upper()}"
            )

        self.full_clean()

        super().save(*args, **kwargs)

    # ========================================================
    # STRING REPRESENTATION
    # ========================================================

    def __str__(self):
        return self.recommendation_number
