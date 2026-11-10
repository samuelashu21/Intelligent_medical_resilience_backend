import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# ==========================================
# Base Abstract Model
# ==========================================


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ==========================================
# Reference & Lookup Models
# ==========================================


class Country(models.Model):
    """
    Country reference table using ISO 3166-1 alpha-2 codes.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=2,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    is_active = models.BooleanField(default=True)

    def clean(self):
        self.code = self.code.strip().upper()

        if len(self.code) != 2 or not self.code.isalpha():
            raise ValidationError({"code": "Use a two-letter ISO country code."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


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
        return f"{self.code}\n{self.name}"


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


class ATCClassification(models.Model):
    """
    Hierarchical Anatomical Therapeutic Chemical classification.

    The ATC hierarchy has up to five levels.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=7,
        unique=True,
        db_index=True,
    )

    name = models.CharField(max_length=255)

    level = models.PositiveSmallIntegerField()

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(
                fields=["level", "is_active"],
                name="atc_level_active_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(level__gte=1) & Q(level__lte=5),
                name="atc_level_between_1_5",
            ),
        ]

    def clean(self):
        super().clean()

        self.code = self.code.strip().upper()

        if self.level < 1 or self.level > 5:
            raise ValidationError({"level": "ATC level must be between 1 and 5."})

        if self.level == 1 and self.parent_id:
            raise ValidationError(
                {"parent": "Level 1 ATC classifications cannot have parents."}
            )

        if self.level > 1:
            if not self.parent_id:
                raise ValidationError(
                    {"parent": "Levels 2–5 require a parent classification."}
                )

            if self.parent.level != self.level - 1:
                raise ValidationError(
                    {
                        "parent": (
                            "Parent classification must be exactly "
                            "one level above this classification."
                        )
                    }
                )

            if not self.code.startswith(self.parent.code):
                raise ValidationError(
                    {
                        "code": (
                            "The classification code must begin with "
                            "its parent's code."
                        )
                    }
                )

        if self.parent_id and self.pk == self.parent_id:
            raise ValidationError(
                {"parent": "A classification cannot be its own parent."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


# ==========================================
# Core Medicine Model
# ==========================================


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

    atc_classification = models.ForeignKey(
        "medicines.ATCClassification",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="medicines",
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
                condition=(Q(strength_value__isnull=True) | Q(strength_value__gt=0)),
                name="medicine_strength_positive",
            ),
            models.CheckConstraint(
                condition=(Q(pack_size__isnull=True) | Q(pack_size__gt=0)),
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
            raise ValidationError(
                {"generic_name": "Generic medicine name is required."}
            )

        if self.strength_value is not None and self.strength_value <= 0:
            raise ValidationError({"strength_value": "Strength must be positive."})

        if self.pack_size is not None and self.pack_size <= 0:
            raise ValidationError({"pack_size": "Pack size must be positive."})

        if bool(self.strength_value) != bool(self.strength_unit_id):
            raise ValidationError(
                "Provide both strength value and strength unit, or neither."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        strength = f" {self.strength_display}" if self.strength_display else ""

        return f"{self.generic_name}{strength}"


# ==========================================
# Phase 11 Extension Models (Dependent on Medicine)
# ==========================================


class EssentialMedicineList(models.Model):
    """
    A country-specific essential medicines list and its version.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="essential_medicine_lists",
    )

    name = models.CharField(max_length=255)

    version = models.CharField(max_length=50)

    effective_from = models.DateField()

    effective_until = models.DateField(
        null=True,
        blank=True,
    )

    source_reference = models.URLField(blank=True)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["country__name", "-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "version"],
                name="unique_country_eml_version",
            ),
            models.CheckConstraint(
                condition=(
                    Q(effective_until__isnull=True)
                    | Q(effective_until__gte=models.F("effective_from"))
                ),
                name="eml_valid_date_range",
            ),
        ]

    def clean(self):
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValidationError(
                {"effective_until": ("End date cannot be earlier than start date.")}
            )

    def __str__(self):
        return f"{self.country.code} - {self.name} ({self.version})"


class EssentialMedicineItem(models.Model):
    """
    A medicine's inclusion in a specific national EML.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    essential_list = models.ForeignKey(
        EssentialMedicineList,
        on_delete=models.PROTECT,
        related_name="items",
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="essential_list_entries",
    )

    level_of_care = models.CharField(
        max_length=30,
        choices=[
            ("COMMUNITY", "Community"),
            ("PRIMARY", "Primary"),
            ("SECONDARY", "Secondary"),
            ("TERTIARY", "Tertiary"),
            ("ALL", "All levels"),
        ],
        default="ALL",
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["essential_list", "medicine"],
                name="unique_medicine_per_eml",
            ),
        ]

    def __str__(self):
        return f"{self.medicine.generic_name} - " f"{self.essential_list}"


class MedicineNationalCode(models.Model):
    """
    Country-specific medicine identifier.

    A standardized medicine may have different national identifiers
    in different countries.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="medicine_codes",
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="national_codes",
    )

    code = models.CharField(max_length=100)

    description = models.CharField(max_length=255, blank=True)

    is_primary = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["country", "code"],
                name="unique_national_code_per_country",
            ),
            models.UniqueConstraint(
                fields=["country", "medicine"],
                condition=Q(is_primary=True, is_active=True),
                name="one_primary_national_code_per_medicine",
            ),
        ]

    def __str__(self):
        return f"{self.country.code}: {self.code}"


class MedicinePresentation(models.Model):
    """
    A particular commercial or procurement presentation of a medicine.

    Examples:
    - 500 mg tablet, pack of 100
    - 250 mg/5 mL oral suspension, 100 mL bottle
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="presentations",
    )

    presentation_code = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.CharField(max_length=255)

    package_unit = models.ForeignKey(
        MeasurementUnit,
        on_delete=models.PROTECT,
        related_name="medicine_packages",
    )

    units_per_package = models.PositiveIntegerField(default=1)

    barcode = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    manufacturer = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(units_per_package__gt=0),
                name="presentation_units_positive",
            ),
        ]

    def clean(self):
        if self.units_per_package <= 0:
            raise ValidationError(
                {"units_per_package": "Package quantity must be positive."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.description


class MedicineEligibilityRule(models.Model):
    """
    Configurable country, organization or facility-level medicine rules.

    A rule can allow or restrict use of a medicine within a scope.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="eligibility_rules",
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eligibility_rules",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="medicine_eligibility_rules",
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="medicine_eligibility_rules",
    )

    is_allowed = models.BooleanField(default=True)

    reason = models.TextField()

    effective_from = models.DateField()

    effective_until = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["medicine__generic_name", "-effective_from"]
        indexes = [
            models.Index(
                fields=["medicine", "is_active"],
                name="elig_medicine_active_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(effective_until__isnull=True)
                    | Q(effective_until__gte=models.F("effective_from"))
                ),
                name="eligibility_valid_date_range",
            ),
        ]

    def clean(self):
        super().clean()

        if self.effective_until and self.effective_until < self.effective_from:
            raise ValidationError(
                {"effective_until": "Invalid eligibility date range."}
            )

        if self.facility_id and not self.organization_id:
            raise ValidationError(
                {
                    "organization": (
                        "A facility-level rule must specify its organization."
                    )
                }
            )

        if self.facility_id and self.organization_id:
            if self.facility.organization_id != self.organization_id:
                raise ValidationError(
                    {
                        "facility": (
                            "The facility must belong to the selected organization."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.medicine.generic_name} - "
            f"{'Allowed' if self.is_allowed else 'Restricted'}"
        )


class MedicineImportBatch(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("COMPLETED_WITH_ERRORS", "Completed with errors"),
        ("FAILED", "Failed"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicine_import_batches",
    )

    filename = models.CharField(max_length=255)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)

    summary = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} - {self.status}"


class MedicineImportRow(models.Model):
    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("UPDATED", "Updated"),
        ("FAILED", "Failed"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    batch = models.ForeignKey(
        MedicineImportBatch,
        on_delete=models.CASCADE,
        related_name="rows",
    )

    row_number = models.PositiveIntegerField()

    medicine_code = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
    )

    message = models.TextField(blank=True)

    source_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"],
                name="unique_import_row_per_batch",
            ),
        ]

    def __str__(self):
        return f"Row {self.row_number}: {self.status}"
