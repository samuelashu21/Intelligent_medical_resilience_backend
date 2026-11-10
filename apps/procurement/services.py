from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.replenishment.models import (
    ReplenishmentRequest,
    ReplenishmentRequestLine,
)

from apps.suppliers.models import Supplier

from apps.procurement.models import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionStatus,
    SupplierQuotation,
    SupplierQuotationLine,
    QuotationStatus,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)

# ============================================================
# PROCUREMENT AUDIT
# ============================================================


def record_procurement_audit(
    *,
    user,
    action,
    target_type,
    target_id,
    description,
    organization,
    changes=None,
    metadata=None,
):
    from apps.audit.models import AuditEvent

    return AuditEvent.objects.create(
        actor=user,
        category="SYSTEM",
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        description=description,
        organization=organization,
        changes=changes or {},
        metadata=metadata or {},
    )


# ============================================================
# SUPPLIER VALIDATION
# ============================================================


def validate_approved_supplier(supplier_id):
    supplier = Supplier.objects.filter(
        pk=supplier_id,
        status="APPROVED",
    ).first()

    if not supplier:
        raise ValidationError(
            "The selected supplier does not exist or is not approved."
        )

    return supplier


# ============================================================
# PURCHASE REQUISITION
# ============================================================


@transaction.atomic
def create_purchase_requisition(
    *,
    replenishment_request_id,
    user,
    justification=None,
    notes="",
):
    """
    Convert an approved replenishment request into a requisition.
    """

    request = ReplenishmentRequest.objects.select_for_update().get(
        pk=replenishment_request_id
    )

    if request.status != ReplenishmentRequest.Status.APPROVED:
        raise ValidationError(
            "Only fully approved replenishment requests "
            "can become purchase requisitions."
        )

    if hasattr(request, "purchase_requisition"):
        raise ValidationError("A purchase requisition already exists for this request.")

    source_lines = list(
        ReplenishmentRequestLine.objects.filter(request=request).select_related(
            "medicine"
        )
    )

    approved_lines = [
        line
        for line in source_lines
        if line.approved_quantity is not None and line.approved_quantity > 0
    ]

    if not approved_lines:
        raise ValidationError(
            "The replenishment request has no positively approved lines."
        )

    requisition = PurchaseRequisition(
        replenishment_request=request,
        organization=request.organization,
        requested_by=user,
        justification=(justification or request.justification),
        notes=notes,
    )

    requisition.save()

    for source_line in approved_lines:
        PurchaseRequisitionLine.objects.create(
            requisition=requisition,
            replenishment_line=source_line,
            medicine=source_line.medicine,
            quantity=source_line.approved_quantity,
            unit_code=source_line.unit_code,
        )

    # --------------------------------------------------------
    # PROCUREMENT AUDIT: REQUISITION CREATED
    # --------------------------------------------------------

    record_procurement_audit(
        user=user,
        action="PURCHASE_REQUISITION_CREATED",
        target_type="PurchaseRequisition",
        target_id=requisition.pk,
        description=(
            f"Purchase requisition {requisition.requisition_number} "
            f"created from {request.request_number}."
        ),
        organization=requisition.organization,
        metadata={
            "replenishment_request_id": str(request.pk),
        },
    )

    return requisition


@transaction.atomic
def submit_purchase_requisition(requisition_id, user):
    requisition = PurchaseRequisition.objects.select_for_update().get(pk=requisition_id)

    if requisition.status != PurchaseRequisitionStatus.DRAFT:
        raise ValidationError("Only draft requisitions can be submitted.")

    if not requisition.items.exists():
        raise ValidationError("A requisition must contain at least one item.")

    requisition.status = PurchaseRequisitionStatus.SUBMITTED
    requisition.submitted_by = user
    requisition.submitted_at = timezone.now()

    requisition.save(
        update_fields=[
            "status",
            "submitted_by",
            "submitted_at",
            "updated_at",
        ]
    )

    return requisition


@transaction.atomic
def approve_purchase_requisition(requisition_id, user):
    requisition = PurchaseRequisition.objects.select_for_update().get(pk=requisition_id)

    if requisition.status != PurchaseRequisitionStatus.SUBMITTED:
        raise ValidationError("Only submitted requisitions can be approved.")

    if requisition.requested_by_id == user.pk:
        raise ValidationError(
            "The requisition creator cannot approve their own requisition."
        )

    requisition.status = PurchaseRequisitionStatus.APPROVED
    requisition.approved_by = user
    requisition.approved_at = timezone.now()

    requisition.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    return requisition


# ============================================================
# SUPPLIER QUOTATIONS
# ============================================================


@transaction.atomic
def add_supplier_quotation(
    *,
    requisition_id,
    supplier_id,
    quotation_number,
    currency,
    valid_until,
    delivery_days,
    submitted_by,
    items,
    quotation_date=None,
    payment_terms="",
    delivery_terms="",
    notes="",
):
    requisition = PurchaseRequisition.objects.select_for_update().get(pk=requisition_id)

    if requisition.status not in [
        PurchaseRequisitionStatus.SUBMITTED,
        PurchaseRequisitionStatus.APPROVED,
    ]:
        raise ValidationError(
            "Quotations can only be added to submitted or approved requisitions."
        )

    supplier = validate_approved_supplier(supplier_id)

    if not items:
        raise ValidationError("A supplier quotation must contain at least one item.")

    quotation = SupplierQuotation.objects.create(
        requisition=requisition,
        supplier=supplier,
        quotation_number=quotation_number,
        currency=currency.upper(),
        quotation_date=quotation_date or timezone.localdate(),
        valid_until=valid_until,
        delivery_days=delivery_days,
        payment_terms=payment_terms,
        delivery_terms=delivery_terms,
        submitted_by=submitted_by,
        notes=notes,
    )

    seen_lines = set()

    for item in items:
        line_id = item["requisition_line_id"]

        if str(line_id) in seen_lines:
            raise ValidationError(
                "A requisition line cannot appear twice in one quotation."
            )

        seen_lines.add(str(line_id))

        requisition_line = (
            requisition.items.select_for_update().filter(pk=line_id).first()
        )

        if not requisition_line:
            raise ValidationError("A quoted line does not belong to this requisition.")

        SupplierQuotationLine.objects.create(
            quotation=quotation,
            requisition_line=requisition_line,
            quantity=Decimal(str(item["quantity"])),
            unit_price=Decimal(str(item["unit_price"])),
            notes=item.get("notes", ""),
        )

    return quotation


# ============================================================
# QUOTATION EVALUATION
# ============================================================


def calculate_quotation_total(quotation):
    total = sum(
        (line.line_total for line in quotation.items.all()),
        Decimal("0"),
    )

    return total


def evaluate_quotation(quotation):
    """
    Return a basic, transparent quotation comparison summary.

    Only compare quotations with the same currency and requisition.
    This is not an automated award decision.
    """

    if quotation.valid_until < timezone.localdate():
        raise ValidationError("This quotation has expired.")

    lines = list(quotation.items.select_related("requisition_line"))

    if not lines:
        raise ValidationError("The quotation contains no line items.")

    return {
        "quotation_id": str(quotation.pk),
        "quotation_number": quotation.quotation_number,
        "supplier": quotation.supplier.name,
        "currency": quotation.currency,
        "total": str(calculate_quotation_total(quotation)),
        "delivery_days": quotation.delivery_days,
        "line_count": len(lines),
        "valid_until": quotation.valid_until.isoformat(),
    }


# ============================================================
# SUPPLIER QUOTATION SELECTION
# ============================================================


@transaction.atomic
def select_supplier_quotation(
    *,
    quotation_id,
    user,
    justification,
):
    quotation = (
        SupplierQuotation.objects.select_for_update()
        .select_related(
            "requisition",
            "supplier",
        )
        .get(pk=quotation_id)
    )

    requisition = PurchaseRequisition.objects.select_for_update().get(
        pk=quotation.requisition_id
    )

    if requisition.status != PurchaseRequisitionStatus.APPROVED:
        raise ValidationError(
            "The requisition must be approved before selecting a quotation."
        )

    if quotation.status not in [
        QuotationStatus.RECEIVED,
        QuotationStatus.UNDER_REVIEW,
    ]:
        raise ValidationError("This quotation is not eligible for selection.")

    if quotation.valid_until < timezone.localdate():
        raise ValidationError("Expired quotations cannot be selected.")

    validate_approved_supplier(quotation.supplier_id)

    quoted_line_ids = set(
        quotation.items.values_list(
            "requisition_line_id",
            flat=True,
        )
    )

    required_line_ids = set(requisition.items.values_list("id", flat=True))

    if quoted_line_ids != required_line_ids:
        raise ValidationError(
            "The selected quotation must cover every requisition line. "
            "Partial supplier awards are not supported in this phase."
        )

    # --------------------------------------------------------
    # VALIDATE COMPLETE REQUISITION QUANTITIES
    # --------------------------------------------------------

    quotation_lines = quotation.items.select_related("requisition_line")

    for quotation_line in quotation_lines:
        if quotation_line.quantity != quotation_line.requisition_line.quantity:
            raise ValidationError(
                "This procurement workflow requires each quotation "
                "to cover the complete requisition quantity."
            )

    if not justification or len(justification.strip()) < 10:
        raise ValidationError("Provide a meaningful supplier-selection justification.")

    # Only one quotation may be selected for this requisition
    # in the initial single-supplier purchasing design.
    if (
        requisition.quotations.filter(status=QuotationStatus.SELECTED)
        .exclude(pk=quotation.pk)
        .exists()
    ):
        raise ValidationError(
            "A quotation has already been selected for this requisition."
        )

    quotation.status = QuotationStatus.SELECTED
    quotation.save(update_fields=["status"])

    requisition.notes = (
        requisition.notes + "\nSupplier selection: " + justification.strip()
    ).strip()

    requisition.save(update_fields=["notes", "updated_at"])

    return quotation


# ============================================================
# PURCHASE ORDER CREATION
# ============================================================


@transaction.atomic
def create_purchase_order(
    *,
    quotation_id,
    user,
    tax_amount=Decimal("0"),
    shipping_amount=Decimal("0"),
    expected_delivery_date=None,
    notes="",
):
    quotation = (
        SupplierQuotation.objects.select_for_update()
        .select_related(
            "requisition",
            "supplier",
        )
        .get(pk=quotation_id)
    )

    requisition = PurchaseRequisition.objects.select_for_update().get(
        pk=quotation.requisition_id
    )

    if requisition.status != PurchaseRequisitionStatus.APPROVED:
        raise ValidationError(
            "The requisition must be approved before creating a purchase order."
        )

    if quotation.status != QuotationStatus.SELECTED:
        raise ValidationError(
            "Only a selected supplier quotation can create a purchase order."
        )

    validate_approved_supplier(quotation.supplier_id)

    if quotation.purchase_orders.exists():
        raise ValidationError("A purchase order already exists for this quotation.")

    tax_amount = Decimal(str(tax_amount))
    shipping_amount = Decimal(str(shipping_amount))

    if tax_amount < 0 or shipping_amount < 0:
        raise ValidationError("Tax and shipping amounts cannot be negative.")

    if expected_delivery_date and (expected_delivery_date < timezone.localdate()):
        raise ValidationError("Expected delivery date cannot be in the past.")

    quotation_lines = list(
        quotation.items.select_related(
            "requisition_line",
            "requisition_line__medicine",
        )
    )

    # --------------------------------------------------------
    # CALCULATE SUBTOTAL USING FOUR-DECIMAL PRECISION
    # --------------------------------------------------------

    subtotal = sum(
        (line.line_total.quantize(Decimal("0.0001")) for line in quotation_lines),
        Decimal("0.0000"),
    )

    total = subtotal + tax_amount + shipping_amount

    order = PurchaseOrder(
        requisition=requisition,
        quotation=quotation,
        supplier=quotation.supplier,
        organization=requisition.organization,
        currency=quotation.currency,
        expected_delivery_date=expected_delivery_date,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total_amount=total,
        payment_terms=quotation.payment_terms,
        delivery_terms=quotation.delivery_terms,
        created_by=user,
        notes=notes,
    )

    order.save()

    # --------------------------------------------------------
    # CREATE PURCHASE ORDER LINES
    # --------------------------------------------------------

    for quoted_line in quotation_lines:
        line_total = quoted_line.line_total.quantize(Decimal("0.0001"))

        PurchaseOrderLine.objects.create(
            purchase_order=order,
            requisition_line=quoted_line.requisition_line,
            medicine=quoted_line.requisition_line.medicine,
            quantity=quoted_line.quantity,
            unit_code=quoted_line.requisition_line.unit_code,
            unit_price=quoted_line.unit_price,
            line_total=line_total,
        )

    # --------------------------------------------------------
    # PROCUREMENT AUDIT: PURCHASE ORDER CREATED
    # --------------------------------------------------------

    record_procurement_audit(
        user=user,
        action="PURCHASE_ORDER_CREATED",
        target_type="PurchaseOrder",
        target_id=order.pk,
        description=(f"Purchase order {order.order_number} created."),
        organization=order.organization,
        metadata={
            "supplier_id": str(order.supplier_id),
            "quotation_id": str(quotation.pk),
            "currency": order.currency,
            "total_amount": str(order.total_amount),
        },
    )

    requisition.status = PurchaseRequisitionStatus.CONVERTED
    requisition.save(update_fields=["status", "updated_at"])

    return order


# ============================================================
# PURCHASE ORDER SUBMISSION
# ============================================================


@transaction.atomic
def submit_purchase_order_for_approval(order_id, user):
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)

    if order.status != PurchaseOrderStatus.DRAFT:
        raise ValidationError("Only draft purchase orders can be submitted.")

    if not order.items.exists():
        raise ValidationError("A purchase order must contain at least one line.")

    order.status = PurchaseOrderStatus.PENDING_APPROVAL

    order.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return order


# ============================================================
# PURCHASE ORDER APPROVAL
# ============================================================


@transaction.atomic
def approve_purchase_order(order_id, user):
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)

    if order.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise ValidationError("Only purchase orders pending approval can be approved.")

    if order.created_by_id == user.pk:
        raise ValidationError(
            "The purchase order creator cannot approve their own order."
        )

    validate_approved_supplier(order.supplier_id)

    order.status = PurchaseOrderStatus.APPROVED
    order.approved_by = user
    order.approved_at = timezone.now()

    order.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    return order


# ============================================================
# SEND PURCHASE ORDER
# ============================================================


@transaction.atomic
def send_purchase_order(order_id, user):
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)

    if order.status != PurchaseOrderStatus.APPROVED:
        raise ValidationError("Only approved purchase orders can be sent.")

    order.status = PurchaseOrderStatus.SENT
    order.sent_at = timezone.now()

    order.save(
        update_fields=[
            "status",
            "sent_at",
            "updated_at",
        ]
    )

    return order


# ============================================================
# ACKNOWLEDGE PURCHASE ORDER
# ============================================================


@transaction.atomic
def acknowledge_purchase_order(order_id, user):
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)

    if order.status != PurchaseOrderStatus.SENT:
        raise ValidationError("Only sent purchase orders can be acknowledged.")

    order.status = PurchaseOrderStatus.ACKNOWLEDGED

    order.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return order
