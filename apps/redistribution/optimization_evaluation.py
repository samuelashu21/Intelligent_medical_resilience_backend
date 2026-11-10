from decimal import Decimal


def summarize_allocation_plan(allocations):
    """
    Calculate comparable metrics for any allocation plan.
    """

    total_quantity = Decimal("0")
    total_capacity = Decimal("0")
    route_distances = {}
    recipient_fulfillment = {}

    for item in allocations:

        quantity = Decimal(
            str(item["quantity"])
        )

        capacity = Decimal(
            str(item.get("capacity_units", 0))
        )

        total_quantity += quantity
        total_capacity += capacity

        route_key = (
            item["donor_id"],
            item["recipient_id"],
        )

        route_distances[route_key] = Decimal(
            str(item["distance_km"])
        )

        recipient_key = (
            item["recipient_id"],
            item["medicine_id"],
        )

        recipient_fulfillment[recipient_key] = (
            recipient_fulfillment.get(
                recipient_key,
                Decimal("0"),
            )
            + quantity
        )

    total_distance = sum(
        route_distances.values(),
        Decimal("0"),
    )

    return {
        "total_allocated_quantity": str(total_quantity),
        "total_capacity_used": str(total_capacity),
        "unique_routes": len(route_distances),
        "total_route_distance_km": str(total_distance),
        "recipient_medicine_pairs_served": len(
            recipient_fulfillment
        ),
    }


def calculate_fulfillment_rate(
    *,
    allocated_quantity,
    shortage_quantity,
):
    allocated = Decimal(str(allocated_quantity))
    shortage = Decimal(str(shortage_quantity))

    if shortage <= 0:
        return Decimal("0")

    return min(
        allocated / shortage,
        Decimal("1"),
    ) * Decimal("100")