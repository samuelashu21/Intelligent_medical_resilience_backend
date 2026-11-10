from django.db.models import Count, Avg, Sum, Q

from apps.logistics.shipment_models import (
    Shipment,
    ShipmentStatus,
)


def get_logistics_summary(
    *,
    organization_id=None,
    date_from=None,
    date_to=None,
):
    queryset = Shipment.objects.all()

    if organization_id:
        queryset = queryset.filter(
            transfer__organization_id=organization_id
        )

    if date_from:
        queryset = queryset.filter(
            created_at__date__gte=date_from
        )

    if date_to:
        queryset = queryset.filter(
            created_at__date__lte=date_to
        )

    summary = queryset.aggregate(
        total_shipments=Count("id"),

        dispatched=Count(
            "id",
            filter=Q(status__in=[
                ShipmentStatus.DISPATCHED,
                ShipmentStatus.IN_TRANSIT,
                ShipmentStatus.DELAYED,
                ShipmentStatus.DELIVERED,
                ShipmentStatus.EXCEPTION,
            ]),
        ),

        delivered=Count(
            "id",
            filter=Q(status=ShipmentStatus.DELIVERED),
        ),

        delayed=Count(
            "id",
            filter=Q(status=ShipmentStatus.DELAYED),
        ),

        exceptions=Count(
            "id",
            filter=Q(status=ShipmentStatus.EXCEPTION),
        ),

        total_transport_cost=Sum("transport_cost"),

        average_distance_km=Avg("distance_km"),
    )

    return summary


def get_delivery_time_statistics(queryset=None):

    if queryset is None:
        queryset = Shipment.objects.filter(
            status=ShipmentStatus.DELIVERED,
            dispatched_at__isnull=False,
            delivered_at__isnull=False,
        )

    durations = []

    for shipment in queryset.iterator():

        if shipment.dispatched_at and shipment.delivered_at:

            duration = (
                shipment.delivered_at
                - shipment.dispatched_at
            ).total_seconds() / 3600

            durations.append(duration)

    if not durations:
        return {
            "delivered_shipments": 0,
            "average_delivery_hours": None,
            "minimum_delivery_hours": None,
            "maximum_delivery_hours": None,
        }

    return {
        "delivered_shipments": len(durations),
        "average_delivery_hours": round(
            sum(durations) / len(durations),
            2,
        ),
        "minimum_delivery_hours": round(
            min(durations),
            2,
        ),
        "maximum_delivery_hours": round(
            max(durations),
            2,
        ),
    }