from collections import defaultdict
from decimal import Decimal

from ortools.sat.python import cp_model

QUANTITY_SCALE = 1000
CAPACITY_SCALE = 1_000_000
OBJECTIVE_SCALE = 1_000_000


def to_decimal(value):
    return Decimal(str(value))


def to_quantity_units(value):
    """
    Convert an inventory quantity into integer milli-units.
    """
    scaled = to_decimal(value) * QUANTITY_SCALE

    if scaled != scaled.to_integral_value():
        raise ValueError("Quantity has more than three decimal places.")

    return int(scaled)


def to_capacity_coefficient(capacity_per_inventory_unit):
    """
    Capacity contribution per integer milli-unit.

    Example:
        0.00002 m3 per tablet
        coefficient = round(0.00002 * 1000)
        capacity contribution is represented in micro-m3.
    """
    return int(round(float(capacity_per_inventory_unit) * QUANTITY_SCALE))


def to_capacity_limit(capacity_units):
    return int(round(float(capacity_units) * CAPACITY_SCALE))


def priority_weight(priority):
    weights = {
        "CRITICAL": 10,
        "HIGH": 6,
        "NORMAL": 3,
        "LOW": 1,
    }

    return weights.get(priority, 1)


def optimize_redistribution(
    *,
    donor_batches,
    recipient_needs,
    routes,
    vehicle_capacity_units,
    max_active_routes=None,
    max_solver_seconds=30,
):
    """
    Optimize allocations across multiple medicines and facilities.

    Input structures:

    donor_batches:
    [
        {
            "batch_id": "batch-1",
            "donor_id": "facility-1",
            "medicine_id": "medicine-1",
            "available_quantity": "500.000",
            "capacity_per_unit": "0.00002"
        }
    ]

    recipient_needs:
    [
        {
            "recipient_id": "facility-2",
            "medicine_id": "medicine-1",
            "shortage_quantity": "300.000",
            "priority": "CRITICAL"
        }
    ]

    routes:
    [
        {
            "donor_id": "facility-1",
            "recipient_id": "facility-2",
            "distance_km": "25.5",
            "transport_cost_per_capacity_unit": "2.0"
        }
    ]

    max_active_routes:
        Optional maximum number of routes that can be activated.
    """

    model = cp_model.CpModel()

    vehicle_capacity = to_capacity_limit(vehicle_capacity_units)

    if vehicle_capacity <= 0:
        raise ValueError("Vehicle capacity must be positive.")

    if max_active_routes is not None:
        if max_active_routes < 1:
            raise ValueError("max_active_routes must be at least 1.")

    # -----------------------------------------------------
    # 1. Normalize and index input data
    # -----------------------------------------------------

    donor_map = {}
    recipient_map = {}
    route_map = {}

    for donor in donor_batches:

        donor_map[donor["batch_id"]] = {
            **donor,
            "available_units": to_quantity_units(donor["available_quantity"]),
            "capacity_coefficient": (
                to_capacity_coefficient(donor["capacity_per_unit"])
            ),
        }

    for need in recipient_needs:

        key = (
            need["recipient_id"],
            need["medicine_id"],
        )

        recipient_map[key] = {
            **need,
            "shortage_units": to_quantity_units(need["shortage_quantity"]),
        }

    for route in routes:

        key = (
            route["donor_id"],
            route["recipient_id"],
        )

        if route["donor_id"] == route["recipient_id"]:
            continue

        route_map[key] = route

    # -----------------------------------------------------
    # 2. Generate feasible allocation variables
    # -----------------------------------------------------

    allocations = {}
    route_active = {}

    donor_constraints = defaultdict(list)
    recipient_constraints = defaultdict(list)
    batch_constraints = defaultdict(list)
    route_capacity_constraints = defaultdict(list)

    objective_terms = []
    route_penalty_terms = []

    feasible_candidates = []

    for batch_id, donor in donor_map.items():

        for recipient_key, recipient in recipient_map.items():

            recipient_id, medicine_id = recipient_key

            if donor["medicine_id"] != medicine_id:
                continue

            if donor["donor_id"] == recipient_id:
                continue

            route_key = (
                donor["donor_id"],
                recipient_id,
            )

            route = route_map.get(route_key)

            if route is None:
                continue

            if donor["available_units"] <= 0:
                continue

            if recipient["shortage_units"] <= 0:
                continue

            if donor["capacity_coefficient"] <= 0:
                raise ValueError(
                    "Every medicine requires a positive transport conversion."
                )

            feasible_candidates.append(
                {
                    "batch_id": batch_id,
                    "donor": donor,
                    "recipient": recipient,
                    "route": route,
                    "route_key": route_key,
                }
            )

    if not feasible_candidates:
        return {
            "status": "INFEASIBLE",
            "allocations": [],
            "objective_value": None,
            "solver_statistics": {},
        }

    # -----------------------------------------------------
    # 3. Create route activation variables
    # -----------------------------------------------------

    for candidate in feasible_candidates:

        route_key = candidate["route_key"]

        if route_key not in route_active:

            route_active[route_key] = model.NewBoolVar(f"route_{len(route_active)}")

    # -----------------------------------------------------
    # 3.1 Maximum active routes constraint
    # -----------------------------------------------------

    if max_active_routes is not None:

        model.Add(sum(route_active.values()) <= max_active_routes)

    # -----------------------------------------------------
    # 4. Create allocation variables
    # -----------------------------------------------------

    for index, candidate in enumerate(feasible_candidates):

        batch_id = candidate["batch_id"]
        donor = candidate["donor"]
        recipient = candidate["recipient"]
        route = candidate["route"]
        route_key = candidate["route_key"]

        variable = model.NewIntVar(
            0,
            min(
                donor["available_units"],
                recipient["shortage_units"],
            ),
            f"allocation_{index}",
        )

        allocations[index] = variable

        donor_constraints[
            (
                donor["donor_id"],
                donor["medicine_id"],
            )
        ].append(variable)

        recipient_constraints[
            (
                recipient["recipient_id"],
                recipient["medicine_id"],
            )
        ].append(variable)

        batch_constraints[batch_id].append(variable)

        route_capacity_constraints[route_key].append(
            (
                variable,
                donor["capacity_coefficient"],
            )
        )

        # Benefit per allocated unit approximates the
        # priority-weighted fraction of the shortage fulfilled.

        shortage = recipient["shortage_units"]

        benefit = max(
            1,
            (priority_weight(recipient["priority"]) * OBJECTIVE_SCALE)
            // max(shortage, 1),
        )

        objective_terms.append(variable * benefit)

        # -------------------------------------------------
        # Route distance penalty
        # -------------------------------------------------

        distance = float(route["distance_km"])

        route_penalty = int(round(distance * 100))

        route_penalty_terms.append(route_active[route_key] * route_penalty)

        # -------------------------------------------------
        # Variable transport-cost penalty
        # -------------------------------------------------

        transport_cost = float(
            route.get(
                "transport_cost_per_capacity_unit",
                0,
            )
        )

        capacity_coefficient = donor["capacity_coefficient"]

        cost_per_quantity_unit = int(
            round(distance * transport_cost * capacity_coefficient / 1000)
        )

        if cost_per_quantity_unit > 0:
            objective_terms.append(-variable * cost_per_quantity_unit)

        # -------------------------------------------------
        # Link allocation to route activation
        # -------------------------------------------------

        model.Add(
            variable
            <= (
                min(
                    donor["available_units"],
                    recipient["shortage_units"],
                )
                * route_active[route_key]
            )
        )

    # -----------------------------------------------------
    # 5. Donor stock constraints
    # -----------------------------------------------------

    for donor_key, variables in donor_constraints.items():

        donor_id, medicine_id = donor_key

        maximum = sum(
            donor["available_units"]
            for donor in donor_map.values()
            if (donor["donor_id"] == donor_id and donor["medicine_id"] == medicine_id)
        )

        model.Add(sum(variables) <= maximum)

    # -----------------------------------------------------
    # 6. Recipient shortage constraints
    # -----------------------------------------------------

    for recipient_key, variables in recipient_constraints.items():

        recipient = recipient_map[recipient_key]

        model.Add(sum(variables) <= recipient["shortage_units"])

    # -----------------------------------------------------
    # 7. Individual batch constraints
    # -----------------------------------------------------

    for batch_id, variables in batch_constraints.items():

        model.Add(sum(variables) <= donor_map[batch_id]["available_units"])

    # -----------------------------------------------------
    # 8. Transport capacity constraints
    # -----------------------------------------------------

    for route_key, entries in route_capacity_constraints.items():

        capacity_expression = sum(
            variable * coefficient for variable, coefficient in entries
        )

        model.Add(capacity_expression <= vehicle_capacity * route_active[route_key])

    # -----------------------------------------------------
    # 9. Objective
    # -----------------------------------------------------

    total_benefit = sum(objective_terms)

    total_route_penalty = sum(route_penalty_terms)

    model.Maximize(total_benefit - total_route_penalty)

    # -----------------------------------------------------
    # 10. Solve
    # -----------------------------------------------------

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = max_solver_seconds

    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    status_names = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }

    status_name = status_names.get(
        status,
        "UNKNOWN",
    )

    if status not in [
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ]:
        return {
            "status": status_name,
            "allocations": [],
            "objective_value": None,
            "solver_statistics": {
                "wall_time": solver.WallTime(),
                "branches": solver.NumBranches(),
                "conflicts": solver.NumConflicts(),
            },
        }

    # -----------------------------------------------------
    # 11. Extract allocations
    # -----------------------------------------------------

    results = []

    for index, candidate in enumerate(feasible_candidates):

        quantity_units = solver.Value(allocations[index])

        if quantity_units <= 0:
            continue

        donor = candidate["donor"]
        recipient = candidate["recipient"]
        route = candidate["route"]

        quantity = Decimal(quantity_units) / Decimal(QUANTITY_SCALE)

        results.append(
            {
                "batch_id": candidate["batch_id"],
                "donor_id": donor["donor_id"],
                "recipient_id": recipient["recipient_id"],
                "medicine_id": donor["medicine_id"],
                "quantity": str(quantity),
                "distance_km": str(route["distance_km"]),
                "priority": recipient["priority"],
                "capacity_units": str(
                    quantity * to_decimal(donor["capacity_per_unit"])
                ),
            }
        )

    # -----------------------------------------------------
    # 12. Return optimization results
    # -----------------------------------------------------

    return {
        "status": status_name,
        "allocations": results,
        "objective_value": solver.ObjectiveValue(),
        "solver_statistics": {
            "wall_time": solver.WallTime(),
            "branches": solver.NumBranches(),
            "conflicts": solver.NumConflicts(),
        },
    }
