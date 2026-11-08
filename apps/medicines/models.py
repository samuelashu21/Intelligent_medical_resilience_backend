import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
 

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TherapeuticCategory(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    description = models.TextField(blank=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Therapeutic categories"

    def __str__(self):
        return f"{self.code} - {self.name}"


class DosageForm(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=40,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdministrationRoute(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=40,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MeasurementUnit(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=30,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    symbol = models.CharField(max_length=30, blank=True)

    unit_type = models.CharField(
        max_length=30,
        choices=[
            ("COUNT", "Count"),
            ("MASS", "Mass"),
            ("VOLUME", "Volume"),
            ("OTHER", "Other"),
        ],
        default="COUNT",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Medicine(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=80,
        unique=True,
    )

    generic_name = models.CharField(
        max_length=255,
        db_index=True,
    )

    brand_name = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    description = models.TextField(blank=True)

    therapeutic_category = models.ForeignKey(
        TherapeuticCategory,
        on_delete=models.PROTECT,
        related_name="medicines",
        null=True,
        blank=True,
    )

    dosage_form = models.ForeignKey(
        DosageForm,
        on_delete=models.PROTECT,
        related_name="medicines",
    )

    administration_route = models.ForeignKey(
        AdministrationRoute,
        on_delete=models.PROTECT,
        related_name="medicines",
        null=True,
        blank=True,
    )

    strength_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
    )

    strength_unit = models.ForeignKey(
        MeasurementUnit,
        on_delete=models.PROTECT,
        related_name="strength_medicines",
        null=True,
        blank=True,
    )

    strength_display = models.CharField(
        max_length=100,
        blank=True,
        help_text="Human-readable strength, e.g. 500 mg or 250 mg/5 mL.",
    )

    dispensing_unit = models.ForeignKey(
        MeasurementUnit,
        on_delete=models.PROTECT,
        related_name="dispensed_medicines",
        null=True,
        blank=True,
    )

    pack_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of dispensing units per pack, if applicable.",
    )

    atc_code = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Anatomical Therapeutic Chemical classification code.",
    )

    national_code = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    is_essential = models.BooleanField(default=False)

    is_controlled = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["generic_name", "strength_display"]
        indexes = [
            models.Index(
                fields=["generic_name", "is_active"],
                name="med_generic_active_idx",
            ),
            models.Index(
                fields=["atc_code"],
                name="med_atc_code_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(strength_value__isnull=True)
                    | Q(strength_value__gt=0)
                ),
                name="medicine_strength_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(pack_size__isnull=True)
                    | Q(pack_size__gt=0)
                ),
                name="medicine_pack_size_positive",
            ),
        ]

    def clean(self):
        super().clean()

        self.generic_name = (self.generic_name or "").strip()
        self.brand_name = (self.brand_name or "").strip()
        self.code = (self.code or "").strip().upper()
        self.atc_code = (self.atc_code or "").strip().upper()

        if not self.generic_name:
            raise ValidationError({
                "generic_name": "Generic medicine name is required."
            })

        if self.strength_value is not None and self.strength_value <= 0:
            raise ValidationError({
                "strength_value": "Strength must be positive."
            })

        if self.pack_size is not None and self.pack_size <= 0:
            raise ValidationError({
                "pack_size": "Pack size must be positive."
            })

        if bool(self.strength_value) != bool(self.strength_unit_id):
            raise ValidationError(
                "Provide both strength value and strength unit, or neither."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        strength = (
            f" {self.strength_display}"
            if self.strength_display else ""
        )

        return f"{self.generic_name}{strength}"