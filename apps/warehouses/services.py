from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event

from apps.warehouses.models import (
    Warehouse,
    WarehouseManagerAssignment,
    WarehouseStatus,
    WarehouseTemperatureReading,
)


def audit_warehouse(
    *,
    request,
    action,
    warehouse,
    description,
    changes=None,
):
    return record_audit_event(
        request=request,
        category="SYSTEM",
        action=action,
        target_type="Warehouse",
        target_id=str(warehouse.pk),
        description=description,
        changes=changes or {},
        organization=warehouse.organization,
        facility=warehouse.facility,
    )


@transaction.atomic
def activate_warehouse(*, warehouse_id, request=None):
    warehouse = Warehouse.objects.select_for_update().get(pk=warehouse_id)

    if warehouse.status not in [
        WarehouseStatus.DRAFT,
        WarehouseStatus.MAINTENANCE,
    ]:
        raise ValidationError("Only draft or maintenance warehouses can be activated.")

    warehouse.status = WarehouseStatus.ACTIVE
    warehouse.save()

    if request:
        audit_warehouse(
            request=request,
            action="WAREHOUSE_ACTIVATED",
            warehouse=warehouse,
            description=f"Warehouse {warehouse.code} activated.",
        )

    return warehouse


@transaction.atomic
def suspend_warehouse(
    *,
    warehouse_id,
    reason,
    request=None,
):
    warehouse = Warehouse.objects.select_for_update().get(pk=warehouse_id)

    if warehouse.status != WarehouseStatus.ACTIVE:
        raise ValidationError("Only active warehouses can be suspended.")

    warehouse.status = WarehouseStatus.SUSPENDED
    warehouse.notes = f"{warehouse.notes}\nSuspension reason: {reason}".strip()
    warehouse.save()

    if request:
        audit_warehouse(
            request=request,
            action="WAREHOUSE_SUSPENDED",
            warehouse=warehouse,
            description=f"Warehouse suspended: {reason}",
        )

    return warehouse


@transaction.atomic
def set_warehouse_maintenance(
    *,
    warehouse_id,
    reason,
    request=None,
):
    warehouse = Warehouse.objects.select_for_update().get(pk=warehouse_id)

    if warehouse.status != WarehouseStatus.ACTIVE:
        raise ValidationError("Only active warehouses can enter maintenance.")

    warehouse.status = WarehouseStatus.MAINTENANCE
    warehouse.notes = f"{warehouse.notes}\nMaintenance reason: {reason}".strip()
    warehouse.save()

    if request:
        audit_warehouse(
            request=request,
            action="WAREHOUSE_MAINTENANCE",
            warehouse=warehouse,
            description=f"Warehouse maintenance: {reason}",
        )

    return warehouse


@transaction.atomic
def close_warehouse(
    *,
    warehouse_id,
    reason,
    request=None,
):
    warehouse = Warehouse.objects.select_for_update().get(pk=warehouse_id)

    if warehouse.status == WarehouseStatus.CLOSED:
        return warehouse

    warehouse.status = WarehouseStatus.CLOSED
    warehouse.notes = f"{warehouse.notes}\nClosure reason: {reason}".strip()
    warehouse.save()

    if request:
        audit_warehouse(
            request=request,
            action="WAREHOUSE_CLOSED",
            warehouse=warehouse,
            description=f"Warehouse closed: {reason}",
        )

    return warehouse


@transaction.atomic
def assign_warehouse_manager(
    *,
    warehouse,
    user,
    assigned_by,
    valid_from=None,
    valid_until=None,
):
    if warehouse.status == WarehouseStatus.CLOSED:
        raise ValidationError("Cannot assign a manager to a closed warehouse.")

    if not user.is_active:
        raise ValidationError("Cannot assign an inactive user.")

    if valid_until and valid_from and valid_until <= valid_from:
        raise ValidationError("Assignment end must be after assignment start.")

    assignment = WarehouseManagerAssignment.objects.create(
        warehouse=warehouse,
        user=user,
        assigned_by=assigned_by,
        valid_from=valid_from or timezone.now(),
        valid_until=valid_until,
    )

    return assignment


@transaction.atomic
def revoke_warehouse_manager(*, assignment_id):
    assignment = WarehouseManagerAssignment.objects.select_for_update().get(
        pk=assignment_id
    )

    assignment.is_active = False
    assignment.save(update_fields=["is_active"])

    return assignment


def classify_temperature_reading(reading):
    """
    Compare a reading with the configured limits of its zone.

    If limits are absent, the reading is classified as UNCONFIGURED,
    not automatically safe.
    """

    zone = reading.zone

    if not zone:
        return {
            "status": "UNCONFIGURED",
            "message": "No storage zone is associated with this reading.",
        }

    if zone.minimum_temperature is None or zone.maximum_temperature is None:
        return {
            "status": "UNCONFIGURED",
            "message": "Temperature limits are not configured.",
        }

    if reading.temperature < zone.minimum_temperature:
        return {
            "status": "BELOW_RANGE",
            "message": "Temperature is below the configured zone range.",
        }

    if reading.temperature > zone.maximum_temperature:
        return {
            "status": "ABOVE_RANGE",
            "message": "Temperature is above the configured zone range.",
        }

    return {
        "status": "WITHIN_RANGE",
        "message": "Temperature is within the configured zone range.",
    }


def get_warehouse_temperature_summary(warehouse):
    readings = WarehouseTemperatureReading.objects.filter(
        warehouse=warehouse
    ).select_related("zone")

    latest = readings.first()

    if not latest:
        return {
            "total_readings": 0,
            "latest_reading": None,
            "latest_status": "NO_DATA",
        }

    classification = classify_temperature_reading(latest)

    return {
        "total_readings": readings.count(),
        "latest_reading": {
            "temperature": str(latest.temperature),
            "humidity": (str(latest.humidity) if latest.humidity is not None else None),
            "recorded_at": latest.recorded_at,
            "zone": latest.zone.name if latest.zone else None,
        },
        "latest_status": classification["status"],
        "latest_message": classification["message"],
    }


def get_warehouse_capacity_summary(warehouse):
    latest = warehouse.capacity_snapshots.first()

    if not latest:
        return {
            "used_capacity": None,
            "available_capacity": None,
            "utilization_percentage": None,
            "capacity_unit": warehouse.capacity_unit,
        }

    total = latest.used_capacity + latest.available_capacity

    utilization = float(latest.used_capacity / total * 100) if total > 0 else 0

    return {
        "used_capacity": str(latest.used_capacity),
        "available_capacity": str(latest.available_capacity),
        "utilization_percentage": round(utilization, 2),
        "capacity_unit": latest.capacity_unit,
        "measured_at": latest.measured_at,
    }
