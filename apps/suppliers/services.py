from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.suppliers.models import (
    Supplier,
    SupplierLicense,
    SupplierPerformanceRecord,
    SupplierStatus,
)


def record_supplier_audit(
    *,
    request,
    action,
    supplier,
    description,
    changes=None,
):
    """
    Record supplier changes using the Phase 10 audit service.
    """

    from apps.audit.services import record_audit_event

    return record_audit_event(
        request=request,
        category="SYSTEM",
        action=action,
        target_type="Supplier",
        target_id=str(supplier.pk),
        description=description,
        changes=changes or {},
        organization=supplier.organization,
    )


@transaction.atomic
def approve_supplier(*, supplier_id, approved_by, request=None):
    supplier = Supplier.objects.select_for_update().get(
        pk=supplier_id
    )

    if supplier.status not in [
        SupplierStatus.PENDING,
        SupplierStatus.DRAFT,
    ]:
        raise ValidationError(
            "Only draft or pending suppliers can be approved."
        )

    supplier.status = SupplierStatus.APPROVED
    supplier.approved_by = approved_by
    supplier.approved_at = timezone.now()

    supplier.save()

    if request:
        record_supplier_audit(
            request=request,
            action="SUPPLIER_APPROVED",
            supplier=supplier,
            description=f"Supplier {supplier.code} approved.",
        )

    return supplier


@transaction.atomic
def reject_supplier(
    *,
    supplier_id,
    rejected_by,
    reason,
    request=None,
):
    supplier = Supplier.objects.select_for_update().get(
        pk=supplier_id
    )

    if supplier.status not in [
        SupplierStatus.DRAFT,
        SupplierStatus.PENDING,
    ]:
        raise ValidationError(
            "Only draft or pending suppliers can be rejected."
        )

    supplier.status = SupplierStatus.REJECTED
    supplier.notes = (
        f"{supplier.notes}\nRejection reason: {reason}".strip()
    )

    supplier.save()

    if request:
        record_supplier_audit(
            request=request,
            action="SUPPLIER_REJECTED",
            supplier=supplier,
            description=f"Supplier rejected: {reason}",
        )

    return supplier


@transaction.atomic
def suspend_supplier(
    *,
    supplier_id,
    reason,
    request=None,
):
    supplier = Supplier.objects.select_for_update().get(
        pk=supplier_id
    )

    if supplier.status != SupplierStatus.APPROVED:
        raise ValidationError(
            "Only approved suppliers can be suspended."
        )

    supplier.status = SupplierStatus.SUSPENDED
    supplier.notes = (
        f"{supplier.notes}\nSuspension reason: {reason}".strip()
    )

    supplier.save()

    if request:
        record_supplier_audit(
            request=request,
            action="SUPPLIER_SUSPENDED",
            supplier=supplier,
            description=f"Supplier suspended: {reason}",
        )

    return supplier


@transaction.atomic
def deactivate_supplier(
    *,
    supplier_id,
    reason,
    request=None,
):
    supplier = Supplier.objects.select_for_update().get(
        pk=supplier_id
    )

    if supplier.status == SupplierStatus.INACTIVE:
        return supplier

    supplier.status = SupplierStatus.INACTIVE
    supplier.notes = (
        f"{supplier.notes}\nDeactivation reason: {reason}".strip()
    )

    supplier.save()

    if request:
        record_supplier_audit(
            request=request,
            action="SUPPLIER_DEACTIVATED",
            supplier=supplier,
            description=f"Supplier deactivated: {reason}",
        )

    return supplier


@transaction.atomic
def verify_supplier_license(
    *,
    license_id,
    verified_by,
    request=None,
):
    license_record = SupplierLicense.objects.select_for_update().get(
        pk=license_id
    )

    if (
        license_record.expiry_date
        and license_record.expiry_date < timezone.localdate()
    ):
        raise ValidationError(
            "An expired license cannot be verified as currently valid."
        )

    license_record.verification_status = "VERIFIED"
    license_record.verified_by = verified_by
    license_record.verified_at = timezone.now()

    license_record.save()

    if request:
        record_supplier_audit(
            request=request,
            action="SUPPLIER_LICENSE_VERIFIED",
            supplier=license_record.supplier,
            description=(
                f"License {license_record.license_number} verified."
            ),
        )

    return license_record


def get_supplier_performance(supplier):
    records = SupplierPerformanceRecord.objects.filter(
        supplier=supplier
    )

    completed = records.filter(
        actual_delivery_date__isnull=False
    )

    total_completed = completed.count()

    on_time_count = sum(
        1 for record in completed if record.on_time
    )

    ordered_total = sum(
        record.ordered_quantity for record in records
    )

    received_total = sum(
        record.received_quantity for record in records
    )

    accepted_total = sum(
        record.quality_accepted_quantity for record in records
    )

    return {
        "delivery_records": records.count(),
        "completed_deliveries": total_completed,
        "on_time_deliveries": on_time_count,
        "on_time_rate": (
            round(on_time_count / total_completed * 100, 2)
            if total_completed else None
        ),
        "fulfillment_rate": (
            round(received_total / ordered_total * 100, 2)
            if ordered_total else None
        ),
        "quality_acceptance_rate": (
            round(accepted_total / received_total * 100, 2)
            if received_total else None
        ),
        "ordered_quantity": ordered_total,
        "received_quantity": received_total,
        "quality_accepted_quantity": accepted_total,
    }