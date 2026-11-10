import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def supplier_document_upload_path(instance, filename):
    return (
        f"supplier_documents/{instance.supplier_id}/" f"{uuid.uuid4().hex}_{filename}"
    )


class SupplierType(models.TextChoices):
    MANUFACTURER = "MANUFACTURER", "Manufacturer"
    WHOLESALER = "WHOLESALER", "Wholesaler"
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
    IMPORTER = "IMPORTER", "Importer"
    PUBLIC_AGENCY = "PUBLIC_AGENCY", "Public procurement agency"
    NGO = "NGO", "Non-governmental organization"
    OTHER = "OTHER", "Other"


class SupplierStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING = "PENDING", "Pending approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    SUSPENDED = "SUSPENDED", "Suspended"
    INACTIVE = "INACTIVE", "Inactive"


class Supplier(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(max_length=255)

    supplier_type = models.CharField(
        max_length=30,
        choices=SupplierType.choices,
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True,
    )

    tax_identification_number = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.ForeignKey(
        "medicines.Country",
        on_delete=models.PROTECT,
        related_name="suppliers",
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="suppliers",
        null=True,
        blank=True,
    )

    website = models.URLField(blank=True)

    email = models.EmailField(blank=True)

    phone = models.CharField(max_length=30, blank=True)

    address = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=SupplierStatus.choices,
        default=SupplierStatus.DRAFT,
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_suppliers",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_suppliers",
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["status", "supplier_type"],
                name="supplier_status_type_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="supplier_org_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        self.code = self.code.strip().upper()
        self.name = self.name.strip()

        if not self.name:
            raise ValidationError({"name": "Supplier name is required."})

        if self.status == SupplierStatus.APPROVED:
            if not self.approved_by_id or not self.approved_at:
                raise ValidationError(
                    {
                        "status": (
                            "An approved supplier must have an approver "
                            "and approval timestamp."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class SupplierContact(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="contacts",
    )

    full_name = models.CharField(max_length=255)

    job_title = models.CharField(max_length=150, blank=True)

    email = models.EmailField(blank=True)

    phone = models.CharField(max_length=30, blank=True)

    is_primary = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier"],
                condition=Q(is_primary=True, is_active=True),
                name="one_primary_supplier_contact",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.supplier.name}"


class SupplierAddress(models.Model):
    ADDRESS_TYPES = [
        ("HEAD_OFFICE", "Head office"),
        ("WAREHOUSE", "Warehouse"),
        ("BRANCH", "Branch"),
        ("BILLING", "Billing"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="addresses",
    )

    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPES,
        default="HEAD_OFFICE",
    )

    label = models.CharField(max_length=150, blank=True)

    address_line = models.TextField()

    city = models.CharField(max_length=150, blank=True)

    administrative_area = models.CharField(max_length=150, blank=True)

    postal_code = models.CharField(max_length=30, blank=True)

    country = models.ForeignKey(
        "medicines.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_addresses",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    is_primary = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier"],
                condition=Q(is_primary=True, is_active=True),
                name="one_primary_supplier_address",
            ),
        ]

    def clean(self):
        super().clean()

        if self.latitude is not None:
            if not -90 <= self.latitude <= 90:
                raise ValidationError(
                    {"latitude": "Latitude must be between -90 and 90."}
                )

        if self.longitude is not None:
            if not -180 <= self.longitude <= 180:
                raise ValidationError(
                    {"longitude": "Longitude must be between -180 and 180."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier.name} - {self.address_type}"


class SupplierLicense(models.Model):
    LICENSE_TYPES = [
        ("BUSINESS", "Business license"),
        ("PHARMACEUTICAL", "Pharmaceutical license"),
        ("WHOLESALE", "Wholesale license"),
        ("IMPORT", "Import license"),
        ("DISTRIBUTION", "Distribution license"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="licenses",
    )

    license_type = models.CharField(
        max_length=30,
        choices=LICENSE_TYPES,
    )

    license_number = models.CharField(max_length=150)

    issuing_authority = models.CharField(max_length=255)

    issue_date = models.DateField(null=True, blank=True)

    expiry_date = models.DateField(null=True, blank=True)

    document = models.FileField(
        upload_to=supplier_document_upload_path,
        blank=True,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("VERIFIED", "Verified"),
            ("REJECTED", "Rejected"),
        ],
        default="PENDING",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_supplier_licenses",
    )

    verified_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "license_type", "license_number"],
                name="unique_supplier_license",
            ),
            models.CheckConstraint(
                condition=(
                    Q(expiry_date__isnull=True)
                    | Q(issue_date__isnull=True)
                    | Q(expiry_date__gte=models.F("issue_date"))
                ),
                name="supplier_license_valid_dates",
            ),
        ]

    def clean(self):
        if self.issue_date and self.expiry_date and self.expiry_date < self.issue_date:
            raise ValidationError(
                {"expiry_date": "Expiry cannot be earlier than issue date."}
            )

        if self.verification_status == "VERIFIED":
            if not self.verified_by_id or not self.verified_at:
                raise ValidationError(
                    {
                        "verification_status": (
                            "Verified licenses require a verifier and timestamp."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < timezone.localdate())

    def __str__(self):
        return f"{self.license_type}: {self.license_number}"


class SupplierMedicine(models.Model):
    """
    Medicines and presentations a supplier can provide.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="medicine_offerings",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="supplier_offerings",
    )

    presentation = models.ForeignKey(
        "medicines.MedicinePresentation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_offerings",
    )

    supplier_product_code = models.CharField(
        max_length=100,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="USD",
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    lead_time_days = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    minimum_order_quantity = models.PositiveIntegerField(
        default=1,
    )

    is_preferred = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "medicine", "presentation"],
                name="unique_supplier_medicine_presentation",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=(Q(unit_price__isnull=True) | Q(unit_price__gte=0)),
                name="supplier_unit_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(minimum_order_quantity__gt=0),
                name="supplier_min_order_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["medicine", "is_active"],
                name="supplier_med_active_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.unit_price is not None and self.unit_price < 0:
            raise ValidationError({"unit_price": "Unit price cannot be negative."})

        if self.minimum_order_quantity <= 0:
            raise ValidationError(
                {"minimum_order_quantity": "Minimum order must be positive."}
            )

        if self.presentation_id:
            if self.presentation.medicine_id != self.medicine_id:
                raise ValidationError(
                    {
                        "presentation": (
                            "Presentation must belong to the selected medicine."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier.name} - {self.medicine.generic_name}"


class SupplierContract(models.Model):
    CONTRACT_STATUSES = [
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("TERMINATED", "Terminated"),
        ("SUSPENDED", "Suspended"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="contracts",
    )

    contract_number = models.CharField(max_length=100)

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    start_date = models.DateField()

    end_date = models.DateField()

    currency = models.CharField(max_length=3, default="USD")

    contract_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=CONTRACT_STATUSES,
        default="DRAFT",
    )

    document = models.FileField(
        upload_to=supplier_document_upload_path,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_supplier_contracts",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "contract_number"],
                name="unique_supplier_contract_number",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="supplier_contract_valid_dates",
            ),
            models.CheckConstraint(
                condition=(Q(contract_value__isnull=True) | Q(contract_value__gte=0)),
                name="supplier_contract_value_nonnegative",
            ),
        ]

    def clean(self):
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                raise ValidationError(
                    {"end_date": "Contract end date must follow its start date."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract_number} - {self.supplier.name}"


class SupplierPerformanceRecord(models.Model):
    """
    One performance observation, normally linked to a completed delivery.

    Procurement and delivery modules will create these records later.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="performance_records",
    )

    contract = models.ForeignKey(
        SupplierContract,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="performance_records",
    )

    reference_number = models.CharField(max_length=100)

    expected_delivery_date = models.DateField()

    actual_delivery_date = models.DateField(null=True, blank=True)

    ordered_quantity = models.PositiveIntegerField()

    received_quantity = models.PositiveIntegerField(default=0)

    quality_accepted_quantity = models.PositiveIntegerField(default=0)

    quality_issue_count = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "reference_number"],
                name="unique_supplier_performance_reference",
            ),
            models.CheckConstraint(
                condition=Q(ordered_quantity__gt=0),
                name="performance_order_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(received_quantity__lte=models.F("ordered_quantity")),
                name="performance_received_lte_ordered",
            ),
            models.CheckConstraint(
                condition=Q(
                    quality_accepted_quantity__lte=models.F("received_quantity")
                ),
                name="performance_accepted_lte_received",
            ),
        ]

    def clean(self):
        super().clean()

        if self.contract_id and self.contract.supplier_id != self.supplier_id:
            raise ValidationError(
                {"contract": "Contract must belong to this supplier."}
            )

        if (
            self.actual_delivery_date
            and self.expected_delivery_date
            and self.actual_delivery_date < self.expected_delivery_date
        ):
            # Early delivery is valid. This is intentionally not an error.
            pass

    @property
    def on_time(self):
        if not self.actual_delivery_date:
            return None

        return self.actual_delivery_date <= self.expected_delivery_date

    @property
    def fulfillment_rate(self):
        if not self.ordered_quantity:
            return 0

        return (self.received_quantity / self.ordered_quantity) * 100

    @property
    def quality_acceptance_rate(self):
        if not self.received_quantity:
            return 0

        return (self.quality_accepted_quantity / self.received_quantity) * 100

    def __str__(self):
        return f"{self.supplier.name} - {self.reference_number}"
