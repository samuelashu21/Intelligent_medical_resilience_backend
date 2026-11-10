
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.redistribution.transfer_models import (
    TransferRequest,
    TransferRequestLine,
    TransferStatus,
)

from apps.logistics.shipment_models import (
    Transporter,
    Vehicle,
    Shipment,
    ShipmentLine,
    ShipmentEvent,
    ShipmentException,
    ShipmentStatus,
    ShipmentEventType,
    ShipmentExceptionType,
    VehicleStatus,
    TransporterStatus,
)

from apps.logistics.inventory_integration import (
    post_reserved_dispatch,
)


def record_shipment_audit(
    *,
    user,
    action,
    shipment,
    description,
    metadata=None,
):
    """
    Adapt this wrapper to the exact Phase 10 audit service.
    Do not include passwords, tokens or private credentials.
    """

    from apps.audit.services import record_audit_event

    record_audit_event(
        actor=user,
        category="SYSTEM",
        action=action,
        target_type="Shipment",
        target_id=str(shipment.pk),
        description=description,
        organization=shipment.transfer.organization,
        metadata=metadata or {},
    )


# ==========================================================
# CREATE SHIPMENT
# ==========================================================

@transaction.atomic
def create_shipment(
    *,
    transfer_id,
    transporter_id,
    vehicle_id,
    driver_name,
    driver_phone="",
    planned_dispatch_at=None,
    estimated_delivery_at=None,
    distance_km=None,
    transport_cost=None,
    currency_code="",
    user,
):
    """
    Create a shipment for a fully approved and reserved transfer.

    The entire operation is transaction-protected, including
    the vehicle lock, vehicle assignment, shipment creation,
    shipment lines, events and audit logging.

    No inventory is changed by this function.
    """

    transfer = (
        TransferRequest.objects
        .select_related(
            "donor_facility",
            "recipient_facility",
            "organization",
        )
        .prefetch_related("lines")
        .get(pk=transfer_id)
    )

    if transfer.status != TransferStatus.RESERVED:
        raise ValidationError(
            "Only stock-reserved transfers can create shipments."
        )

    transporter = Transporter.objects.get(
        pk=transporter_id,
        status=TransporterStatus.ACTIVE,
    )

    # Lock the vehicle inside the outer transaction.
    vehicle = (
        Vehicle.objects
        .select_for_update()
        .get(
            pk=vehicle_id,
            transporter=transporter,
            status=VehicleStatus.AVAILABLE,
        )
    )

    if not driver_name or not driver_name.strip():
        raise ValidationError(
            "A driver name is required."
        )

    if (
        planned_dispatch_at
        and estimated_delivery_at
        and estimated_delivery_at < planned_dispatch_at
    ):
        raise ValidationError(
            "Estimated delivery cannot precede dispatch."
        )

    if Shipment.objects.filter(transfer=transfer).exists():
        raise ValidationError(
            "A shipment already exists for this transfer."
        )

    transfer_lines = list(
        transfer.lines.select_related(
            "medicine",
            "batch",
        )
    )

    if not transfer_lines:
        raise ValidationError(
            "The transfer has no lines."
        )

    vehicle.status = VehicleStatus.ASSIGNED
    vehicle.save(update_fields=["status"])

    shipment = Shipment.objects.create(
        transfer=transfer,
        transporter=transporter,
        vehicle=vehicle,
        driver_name=driver_name,
        driver_phone=driver_phone,
        planned_dispatch_at=planned_dispatch_at,
        estimated_delivery_at=estimated_delivery_at,
        distance_km=distance_km,
        transport_cost=transport_cost,
        currency_code=currency_code,
        created_by=user,
        status=ShipmentStatus.DRAFT,
    )

    for transfer_line in transfer_lines:

        if transfer_line.reserved_quantity <= Decimal("0"):
            raise ValidationError(
                "Every shipment line must have a stock reservation."
            )

        quantity = transfer_line.reserved_quantity

        ShipmentLine.objects.create(
            shipment=shipment,
            transfer_line=transfer_line,
            medicine=transfer_line.medicine,
            batch=transfer_line.batch,
            dispatched_quantity=quantity,
            unit_code=transfer_line.unit_code,
        )

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=ShipmentEventType.CREATED,
        description="Shipment created for an approved transfer.",
        recorded_by=user,
    )

    record_shipment_audit(
        user=user,
        action="SHIPMENT_CREATED",
        shipment=shipment,
        description="Shipment created.",
        metadata={
            "transfer_id": str(transfer.pk),
            "vehicle_id": str(vehicle.pk),
            "transporter_id": str(transporter.pk),
        },
    )

    return shipment


# ==========================================================
# MARK SHIPMENT READY
# ==========================================================

@transaction.atomic
def mark_shipment_ready(
    *,
    shipment_id,
    user,
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .select_related(
            "vehicle",
            "transporter",
            "transfer",
        )
        .get(pk=shipment_id)
    )

    if shipment.status != ShipmentStatus.DRAFT:
        raise ValidationError(
            "Only draft shipments can be marked ready."
        )

    if shipment.transporter.status != TransporterStatus.ACTIVE:
        raise ValidationError(
            "Transporter is not active."
        )

    if shipment.vehicle.status != VehicleStatus.ASSIGNED:
        raise ValidationError(
            "Vehicle is not assigned to this shipment."
        )

    if not shipment.lines.exists():
        raise ValidationError(
            "Shipment must contain at least one line."
        )

    for line in shipment.lines.select_related(
        "transfer_line",
        "batch",
        "batch__warehouse",
    ):

        if line.dispatched_quantity <= 0:
            raise ValidationError(
                "Shipment quantity must be positive."
            )

        if (
            line.transfer_line.reserved_quantity
            < line.dispatched_quantity
        ):
            raise ValidationError(
                "Shipment quantity exceeds the reservation."
            )

        if line.batch.expiry_date < timezone.localdate():
            raise ValidationError(
                "Shipment contains an expired batch."
            )

        if not line.batch.warehouse.is_active:
            raise ValidationError(
                "Shipment contains stock from an inactive warehouse."
            )

    shipment.status = ShipmentStatus.READY_FOR_DISPATCH

    shipment.save(
        update_fields=["status", "updated_at"]
    )

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=ShipmentEventType.READY,
        description="Shipment validated and ready for dispatch.",
        recorded_by=user,
    )

    record_shipment_audit(
        user=user,
        action="SHIPMENT_READY",
        shipment=shipment,
        description="Shipment marked ready for dispatch.",
    )

    return shipment


# ==========================================================
# DISPATCH SHIPMENT
# ==========================================================

@transaction.atomic
def dispatch_shipment(
    *,
    shipment_id,
    user,
    dispatch_reference="",
    dispatch_notes="",
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .select_related(
            "transfer",
            "vehicle",
            "transporter",
        )
        .get(pk=shipment_id)
    )

    if shipment.status != ShipmentStatus.READY_FOR_DISPATCH:
        raise ValidationError(
            "Only ready shipments can be dispatched."
        )

    if shipment.transfer.status != TransferStatus.RESERVED:
        raise ValidationError(
            "The associated transfer is not reserved."
        )

    if shipment.vehicle.status != VehicleStatus.ASSIGNED:
        raise ValidationError(
            "The assigned vehicle is not available for dispatch."
        )

    lines = list(
        shipment.lines.select_related(
            "transfer_line",
            "transfer_line__batch",
            "transfer_line__batch__warehouse",
        ).order_by("transfer_line__batch_id")
    )

    if not lines:
        raise ValidationError(
            "Cannot dispatch an empty shipment."
        )

    # All stock operations must succeed or the entire
    # transaction, including shipment status updates, rolls back.
    for line in lines:

        transfer_line = line.transfer_line

        if (
            transfer_line.reserved_quantity
            < line.dispatched_quantity
        ):
            raise ValidationError(
                "Reserved quantity is insufficient for dispatch."
            )

        post_reserved_dispatch(
            transfer_line=transfer_line,
            quantity=line.dispatched_quantity,
            user=user,
            shipment=shipment,
        )

    now = timezone.now()

    shipment.status = ShipmentStatus.DISPATCHED
    shipment.dispatched_at = now
    shipment.dispatch_reference = dispatch_reference
    shipment.dispatch_notes = dispatch_notes

    shipment.save(
        update_fields=[
            "status",
            "dispatched_at",
            "dispatch_reference",
            "dispatch_notes",
            "updated_at",
        ]
    )

    shipment.transfer.status = TransferStatus.DISPATCHED

    shipment.transfer.save(
        update_fields=["status", "updated_at"]
    )

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=ShipmentEventType.DISPATCHED,
        description="Shipment dispatched from the donor facility.",
        recorded_by=user,
    )

    shipment.vehicle.status = VehicleStatus.ASSIGNED
    shipment.vehicle.save(update_fields=["status"])

    record_shipment_audit(
        user=user,
        action="SHIPMENT_DISPATCHED",
        shipment=shipment,
        description="Shipment dispatched.",
        metadata={
            "dispatch_reference": dispatch_reference,
            "dispatched_at": now.isoformat(),
            "line_count": len(lines),
        },
    )

    return shipment


# ==========================================================
# UPDATE SHIPMENT TRACKING
# ==========================================================

@transaction.atomic
def update_shipment_tracking(
    *,
    shipment_id,
    user,
    event_type,
    description="",
    latitude=None,
    longitude=None,
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .get(pk=shipment_id)
    )

    allowed_events = [
        ShipmentEventType.PICKED_UP,
        ShipmentEventType.IN_TRANSIT,
        ShipmentEventType.LOCATION_UPDATE,
        ShipmentEventType.ARRIVED,
    ]

    if event_type not in allowed_events:
        raise ValidationError(
            "This event type is not permitted through tracking updates."
        )

    if shipment.status not in [
        ShipmentStatus.DISPATCHED,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELAYED,
    ]:
        raise ValidationError(
            "Tracking updates require a dispatched shipment."
        )

    if (
        latitude is not None
        and not Decimal("-90") <= Decimal(str(latitude)) <= Decimal("90")
    ):
        raise ValidationError("Invalid latitude.")

    if (
        longitude is not None
        and not Decimal("-180") <= Decimal(str(longitude)) <= Decimal("180")
    ):
        raise ValidationError("Invalid longitude.")

    if event_type in [
        ShipmentEventType.PICKED_UP,
        ShipmentEventType.IN_TRANSIT,
        ShipmentEventType.LOCATION_UPDATE,
    ]:
        shipment.status = ShipmentStatus.IN_TRANSIT

    if event_type == ShipmentEventType.ARRIVED:
        shipment.arrived_at = timezone.now()

    shipment.save(
        update_fields=[
            "status",
            "arrived_at",
            "updated_at",
        ]
    )

    event = ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=event_type,
        description=description,
        latitude=latitude,
        longitude=longitude,
        recorded_by=user,
    )

    record_shipment_audit(
        user=user,
        action="SHIPMENT_TRACKING_UPDATED",
        shipment=shipment,
        description=description or event_type,
        metadata={
            "event_type": event_type,
            "latitude": str(latitude) if latitude is not None else None,
            "longitude": str(longitude) if longitude is not None else None,
        },
    )

    return event


# ==========================================================
# REPORT SHIPMENT DELAY
# ==========================================================

@transaction.atomic
def report_shipment_delay(
    *,
    shipment_id,
    user,
    description,
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .get(pk=shipment_id)
    )

    if shipment.status not in [
        ShipmentStatus.DISPATCHED,
        ShipmentStatus.IN_TRANSIT,
    ]:
        raise ValidationError(
            "Only active shipments can be marked delayed."
        )

    if not description or not description.strip():
        raise ValidationError(
            "A delay explanation is required."
        )

    shipment.status = ShipmentStatus.DELAYED

    shipment.save(
        update_fields=["status", "updated_at"]
    )

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=ShipmentEventType.DELAYED,
        description=description,
        recorded_by=user,
    )

    ShipmentException.objects.create(
        shipment=shipment,
        exception_type=ShipmentExceptionType.DELAY,
        description=description,
        reported_by=user,
    )

    record_shipment_audit(
        user=user,
        action="SHIPMENT_DELAYED",
        shipment=shipment,
        description=description,
    )

    return shipment


# ==========================================================
# REPORT SHIPMENT EXCEPTION
# ==========================================================

@transaction.atomic
def report_shipment_exception(
    *,
    shipment_id,
    user,
    exception_type,
    description,
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .get(pk=shipment_id)
    )

    if shipment.status not in [
        ShipmentStatus.DISPATCHED,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELAYED,
    ]:
        raise ValidationError(
            "Exceptions can only be recorded for active shipments."
        )

    if not description or not description.strip():
        raise ValidationError(
            "An exception description is required."
        )

    valid_types = [
        value for value, _ in ShipmentExceptionType.choices
    ]

    if exception_type not in valid_types:
        raise ValidationError(
            "Invalid shipment exception type."
        )

    exception = ShipmentException.objects.create(
        shipment=shipment,
        exception_type=exception_type,
        description=description,
        reported_by=user,
    )

    shipment.status = ShipmentStatus.EXCEPTION

    shipment.save(
        update_fields=["status", "updated_at"]
    )

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=ShipmentEventType.EXCEPTION,
        description=description,
        recorded_by=user,
    )

    record_shipment_audit(
        user=user,
        action="SHIPMENT_EXCEPTION_REPORTED",
        shipment=shipment,
        description=description,
        metadata={"exception_type": exception_type},
    )

    return exception


# ==========================================================
# RESOLVE SHIPMENT EXCEPTION
# ==========================================================

@transaction.atomic
def resolve_shipment_exception(
    *,
    exception_id,
    user,
    resolution_notes,
):
    exception = (
        ShipmentException.objects
        .select_for_update()
        .select_related("shipment")
        .get(pk=exception_id)
    )

    if exception.resolved:
        raise ValidationError(
            "This exception has already been resolved."
        )

    if not resolution_notes or not resolution_notes.strip():
        raise ValidationError(
            "Resolution notes are required."
        )

    exception.resolved = True
    exception.resolution_notes = resolution_notes
    exception.resolved_by = user
    exception.resolved_at = timezone.now()

    exception.save(
        update_fields=[
            "resolved",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
        ]
    )

    remaining_open = exception.shipment.exceptions.filter(
        resolved=False
    ).exclude(pk=exception.pk).exists()

    if not remaining_open:
        # Do not automatically mark a shipment delivered.
        # An authorized logistics user must explicitly
        # update the shipment's actual delivery state.
        exception.shipment.status = ShipmentStatus.IN_TRANSIT

        exception.shipment.save(
            update_fields=["status", "updated_at"]
        )

    return exception


# ==========================================================
# REPORT SHIPMENT DELIVERED
# ==========================================================

@transaction.atomic
def report_shipment_delivered(
    *,
    shipment_id,
    user,
    delivery_reference="",
    delivery_notes="",
):
    shipment = (
        Shipment.objects
        .select_for_update()
        .select_related("vehicle")
        .get(pk=shipment_id)
    )

    if shipment.status not in [
        ShipmentStatus.DISPATCHED,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELAYED,
        ShipmentStatus.EXCEPTION,
    ]:
        raise ValidationError(
            "This shipment cannot be marked delivered."
        )

    if shipment.exceptions.filter(resolved=False).exists():
        raise ValidationError(
            "Resolve open shipment exceptions before reporting delivery."
        )

    shipment.status = ShipmentStatus.DELIVERED
    shipment.delivered_at = timezone.now()
    shipment.delivery_reference = delivery_reference
    shipment.delivery_notes = delivery_notes

    shipment.save(
        update_fields=[
            "status",
            "delivered_at",
            "delivery_reference",
            "delivery_notes",
            "updated_at",
        ]
    )

    # Release the vehicle after successful delivery reporting.
    shipment.vehicle.status = VehicleStatus.AVAILABLE
    shipment.vehicle.save(update_fields=["status"])

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type=ShipmentEventType.DELIVERED,
        description=(
            "Delivery reported. Recipient stock acceptance "
            "and reconciliation remain pending."
        ),
        recorded_by=user,
    )

    record_shipment_audit(
        user=user,
        action="SHIPMENT_DELIVERY_REPORTED",
        shipment=shipment,
        description="Shipment delivery reported.",
        metadata={
            "delivery_reference": delivery_reference,
            "delivered_at": shipment.delivered_at.isoformat(),
        },
    )

    return shipment
