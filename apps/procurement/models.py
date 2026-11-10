import uuid

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone


class ProcurementStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    CANCELLED = "CANCELLED", "Cancelled"


class PurchaseRequisitionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    CONVERTED = "CONVERTED", "Converted to Purchase Order"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class QuotationStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    SELECTED = "SELECTED", "Selected"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    SENT = "SENT", "Sent to Supplier"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially Received"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


def generate_requisition_number():
    return f"PR-{timezone.now():%Y%m%d}-" f"{uuid.uuid4().hex[:8].upper()}"


def generate_purchase_order_number():
    return f"PO-{timezone.now():%Y%m%d}-" f"{uuid.uuid4().hex[:8].upper()}"


class PurchaseRequisition(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    requisition_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )

    replenishment_request = models.OneToOneField(
        "replenishment.ReplenishmentRequest",
        on_delete=models.PROTECT,
        related_name="purchase_requisition",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="purchase_requisitions",
    )

    status = models.CharField(
        max_length=30,
        choices=PurchaseRequisitionStatus.choices,
        default=PurchaseRequisitionStatus.DRAFT,
        db_index=True,
    )

    justification = models.TextField()

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchase_requisitions",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submitted_purchase_requisitions",
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
        related_name="approved_purchase_requisitions",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="proc_req_org_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="proc_req_status_date_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.requisition_number:
            self.requisition_number = generate_requisition_number()

        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        if self.replenishment_request_id:
            if self.organization_id != self.replenishment_request.organization_id:
                raise ValidationError(
                    "Requisition organization must match "
                    "the replenishment request organization."
                )

            if self.replenishment_request.status != "APPROVED":
                raise ValidationError(
                    "Only approved replenishment requests "
                    "can become purchase requisitions."
                )

        if self.status == PurchaseRequisitionStatus.APPROVED:
            if not self.approved_by_id or not self.approved_at:
                raise ValidationError(
                    "Approved requisitions require approval metadata."
                )

        if self.status == PurchaseRequisitionStatus.SUBMITTED:
            if not self.submitted_by_id or not self.submitted_at:
                raise ValidationError(
                    "Submitted requisitions require submission metadata."
                )

    def __str__(self):
        return self.requisition_number


class PurchaseRequisitionLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.PROTECT,
        related_name="items",
    )

    replenishment_line = models.OneToOneField(
        "replenishment.ReplenishmentRequestLine",
        on_delete=models.PROTECT,
        related_name="purchase_requisition_line",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="purchase_requisition_lines",
    )

    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    unit_code = models.CharField(max_length=30)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="proc_req_line_qty_positive",
            )
        ]

    def clean(self):
        if self.replenishment_line_id:
            source = self.replenishment_line

            if source.request_id != self.requisition.replenishment_request_id:
                raise ValidationError(
                    "Requisition line must belong to its source "
                    "replenishment request."
                )

            if source.medicine_id != self.medicine_id:
                raise ValidationError(
                    "Medicine does not match the source request line."
                )

            if source.approved_quantity is None:
                raise ValidationError(
                    "The source replenishment line has no approved quantity."
                )

            if self.quantity > source.approved_quantity:
                raise ValidationError(
                    "Requisition quantity cannot exceed the "
                    "approved replenishment quantity."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.requisition} - {self.medicine}"


class SupplierQuotation(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    quotation_number = models.CharField(max_length=100)

    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.PROTECT,
        related_name="quotations",
    )

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="procurement_quotations",
    )

    currency = models.CharField(
        max_length=3,
        default="USD",
    )

    quotation_date = models.DateField(default=timezone.localdate)

    valid_until = models.DateField()

    payment_terms = models.CharField(
        max_length=200,
        blank=True,
    )

    delivery_days = models.PositiveIntegerField()

    delivery_terms = models.CharField(
        max_length=200,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=QuotationStatus.choices,
        default=QuotationStatus.RECEIVED,
        db_index=True,
    )

    document = models.FileField(
        upload_to="procurement/quotations/",
        null=True,
        blank=True,
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_supplier_quotations",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["requisition", "supplier", "quotation_number"],
                name="unique_supplier_quotation_number",
            ),
            models.UniqueConstraint(
                fields=["requisition"],
                condition=Q(status="SELECTED"),
                name="one_selected_quotation_per_requisition",
            ),
            models.CheckConstraint(
                condition=Q(delivery_days__gte=0),
                name="quotation_delivery_days_valid",
            ),
        ]

        indexes = [
            models.Index(
                fields=["requisition", "status"],
                name="quotation_req_status_idx",
            )
        ]

    def clean(self):
        if self.valid_until and self.quotation_date:
            if self.valid_until < self.quotation_date:
                raise ValidationError("Quotation validity cannot end before its date.")

        if self.currency and (len(self.currency) != 3 or not self.currency.isalpha()):
            raise ValidationError("Currency must be a three-letter code.")

        if self.supplier_id and self.supplier.status != "APPROVED":
            raise ValidationError("Only approved suppliers can submit quotations.")

    def save(self, *args, **kwargs):
        self.currency = self.currency.upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.quotation_number


class SupplierQuotationLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    quotation = models.ForeignKey(
        SupplierQuotation,
        on_delete=models.PROTECT,
        related_name="items",
    )

    requisition_line = models.ForeignKey(
        PurchaseRequisitionLine,
        on_delete=models.PROTECT,
        related_name="supplier_quotation_lines",
    )

    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    unit_price = models.DecimalField(
        max_digits=18,
        decimal_places=4,
    )

    notes = models.TextField(blank=True)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "requisition_line"],
                name="unique_quotation_requisition_line",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="quotation_line_qty_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="quotation_line_price_nonnegative",
            ),
        ]

    def clean(self):
        if self.quotation_id and self.requisition_line_id:
            if self.quotation.requisition_id != self.requisition_line.requisition_id:
                raise ValidationError(
                    "Quotation line must belong to the same requisition."
                )

        if self.requisition_line_id:
            if self.quantity > self.requisition_line.quantity:
                raise ValidationError(
                    "Quoted quantity cannot exceed the requisition quantity."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PurchaseOrder(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )

    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )

    quotation = models.ForeignKey(
        SupplierQuotation,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )

    currency = models.CharField(max_length=3)

    order_date = models.DateField(default=timezone.localdate)

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
        db_index=True,
    )

    subtotal = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
    )

    tax_amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
    )

    shipping_amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
    )

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
    )

    payment_terms = models.CharField(max_length=200, blank=True)

    delivery_terms = models.CharField(max_length=200, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchase_orders",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_purchase_orders",
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="po_org_status_idx",
            ),
            models.Index(
                fields=["supplier", "status"],
                name="po_supplier_status_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="po_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(tax_amount__gte=0),
                name="po_tax_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(shipping_amount__gte=0),
                name="po_shipping_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="po_total_nonnegative",
            ),
        ]

    def clean(self):
        if self.quotation_id:
            if self.quotation.requisition_id != self.requisition_id:
                raise ValidationError(
                    "Purchase order quotation must belong to its requisition."
                )

            if self.quotation.supplier_id != self.supplier_id:
                raise ValidationError(
                    "Purchase order supplier must match the quotation supplier."
                )

            if self.quotation.currency != self.currency:
                raise ValidationError(
                    "Purchase order currency must match quotation currency."
                )

        if self.requisition_id and (
            self.organization_id != self.requisition.organization_id
        ):
            raise ValidationError(
                "Purchase order organization must match the requisition."
            )

        if (
            self.expected_delivery_date
            and self.order_date
            and self.expected_delivery_date < self.order_date
        ):
            raise ValidationError("Expected delivery cannot precede the order date.")

        if self.status == PurchaseOrderStatus.APPROVED:
            if not self.approved_by_id or not self.approved_at:
                raise ValidationError(
                    "Approved purchase orders require approval metadata."
                )

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_purchase_order_number()

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class PurchaseOrderLine(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="items",
    )

    requisition_line = models.ForeignKey(
        PurchaseRequisitionLine,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )

    medicine = models.ForeignKey(
        "medicines.Medicine",
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )

    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    unit_code = models.CharField(max_length=30)

    unit_price = models.DecimalField(
        max_digits=18,
        decimal_places=4,
    )

    line_total = models.DecimalField(
        max_digits=20,
        decimal_places=4,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="po_line_qty_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="po_line_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0),
                name="po_line_total_nonnegative",
            ),
        ]

    def clean(self):
        if self.purchase_order_id and self.requisition_line_id:
            if (
                self.purchase_order.requisition_id
                != self.requisition_line.requisition_id
            ):
                raise ValidationError(
                    "Purchase order line must belong to its requisition."
                )

        if self.requisition_line_id:
            if self.medicine_id != self.requisition_line.medicine_id:
                raise ValidationError(
                    "Purchase order medicine does not match requisition."
                )

            if self.quantity > self.requisition_line.quantity:
                raise ValidationError(
                    "Purchase order quantity cannot exceed requisition quantity."
                )

        expected_total = (self.quantity * self.unit_price).quantize(Decimal("0.0001"))

        if self.line_total != expected_total:
            raise ValidationError(
                "Purchase order line total does not match "
                "quantity × unit price rounded to four decimal places."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purchase_order} - {self.medicine}"
