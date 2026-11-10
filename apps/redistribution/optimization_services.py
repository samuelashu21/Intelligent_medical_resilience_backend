
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.facilities.models import Facility
from apps.medicines.models import Medicine
from apps.inventory.models import StockBatch

from apps.redistribution.optimization_models import (
    RedistributionTransportProfile,
    RedistributionOptimizationRun,
    RedistributionOptimizationAllocation,
    OptimizationRunStatus,
)

from apps.redistribution.recommendation_services import (
    get_facility_stock_profile,
    get_facility_eligible_stock,
    get_visible_facilities_for_recommendations,
    get_facility_distance,
    get_recommendation_unit,
    calculate_donor_transferable_quantity,
    calculate_recipient_shortage,
)

from apps.redistribution.optimization_engine import (
    optimize_redistribution,
)


ZERO = Decimal("0")


def get_active_transport_profile(
    *,
    medicine,
    unit_code,
):
    today = timezone.localdate()

    return (
        RedistributionTransportProfile.objects.filter(
            medicine=medicine,
            inventory_unit_code=unit_code,
            is_active=True,
            effective_from__lte=today,
        )
        .filter(
            models.Q(effective_until__isnull=True)
            | models.Q(effective_until__gte=today)
        )
        .order_by("-effective_from")
        .first()
    )


def build_optimization_inputs(
    *,
    user,
    medicine_ids=None,
    amc_months=3,
    maximum_distance_km=None,
):
    # -------------------------------------------------
    # 1. Retrieve only facilities visible to the user
    #    under the optimization-specific permission.
    # -------------------------------------------------

    facilities = list(
        get_visible_facilities_for_recommendations(
            user,
            permission_code="redistribution.optimization.view",
        )
    )

    if medicine_ids:
        medicines = Medicine.objects.filter(pk__in=medicine_ids)
    else:
        medicines = Medicine.objects.all()

    donor_batches = []
    recipient_needs = []
    routes = []

    profiles = {}

    for medicine in medicines:

        unit_code = get_recommendation_unit(medicine)

        transport_profile = get_active_transport_profile(
            medicine=medicine,
            unit_code=unit_code,
        )

        # A medicine without a verified physical capacity
        # conversion cannot participate in mixed-medicine
        # vehicle optimization.
        if transport_profile is None:
            continue

        for facility in facilities:

            profile = get_facility_stock_profile(
                facility=facility,
                medicine_id=medicine.pk,
                amc_months=amc_months,
            )

            if (
                not profile["policy_configured"]
                or profile["daily_demand"] is None
            ):
                continue

            profiles[(facility.pk, medicine.pk)] = profile

            surplus = calculate_donor_transferable_quantity(profile)

            shortage = calculate_recipient_shortage(profile)

            # -------------------------------------------------
            # Build donor stock candidates
            # -------------------------------------------------

            if surplus > ZERO:

                balances = get_facility_eligible_stock(
                    facility_id=facility.pk,
                    medicine_id=medicine.pk,
                )

                remaining_surplus = surplus

                for balance in balances:

                    if remaining_surplus <= ZERO:
                        break

                    available = max(
                        Decimal(str(balance.quantity_on_hand))
                        - Decimal(str(balance.quantity_reserved)),
                        ZERO,
                    )

                    batch_quantity = min(
                        available,
                        remaining_surplus,
                    )

                    if batch_quantity <= ZERO:
                        continue

                    # Only include stock from batches with
                    # sufficient remaining shelf life.
                    expiry_days = (
                        balance.batch.expiry_date - timezone.localdate()
                    ).days

                    required_consumption_days = (
                        batch_quantity / profile["daily_demand"]
                    )

                    if Decimal(expiry_days) < required_consumption_days:
                        continue

                    donor_batches.append(
                        {
                            "batch_id": str(balance.batch_id),
                            "donor_id": str(facility.pk),
                            "medicine_id": str(medicine.pk),
                            "available_quantity": str(batch_quantity),
                            "capacity_per_unit": str(
                                transport_profile.capacity_units_per_inventory_unit
                            ),
                            "expiry_date": balance.batch.expiry_date.isoformat(),
                            "unit_code": unit_code,
                        }
                    )

                    remaining_surplus -= batch_quantity

            # -------------------------------------------------
            # Build recipient shortage candidates
            # -------------------------------------------------

            if shortage > ZERO:

                recipient_needs.append(
                    {
                        "recipient_id": str(facility.pk),
                        "medicine_id": str(medicine.pk),
                        "shortage_quantity": str(shortage),
                        "priority": (
                            "CRITICAL"
                            if (
                                profile["coverage_days"] is not None
                                and profile["coverage_days"] <= 3
                            )
                            else (
                                "HIGH"
                                if (
                                    profile["coverage_days"] is not None
                                    and profile["coverage_days"] <= 7
                                )
                                else "NORMAL"
                            )
                        ),
                        "unit_code": unit_code,
                    }
                )

    # -------------------------------------------------
    # 2. Generate routes for donor/recipient pairs
    # -------------------------------------------------

    donor_facility_ids = {
        item["donor_id"] for item in donor_batches
    }

    recipient_facility_ids = {
        item["recipient_id"] for item in recipient_needs
    }

    facility_lookup = {
        str(facility.pk): facility for facility in facilities
    }

    for donor_id in donor_facility_ids:

        donor_facility = facility_lookup[donor_id]

        for recipient_id in recipient_facility_ids:

            if donor_id == recipient_id:
                continue

            recipient_facility = facility_lookup[recipient_id]

            distance = get_facility_distance(
                donor_facility,
                recipient_facility,
            )

            if distance is None:
                continue

            if (
                maximum_distance_km is not None
                and distance > Decimal(str(maximum_distance_km))
            ):
                continue

            routes.append(
                {
                    "donor_id": donor_id,
                    "recipient_id": recipient_id,
                    "distance_km": str(distance),
                    "transport_cost_per_capacity_unit": "0",
                }
            )

    return {
        "donor_batches": donor_batches,
        "recipient_needs": recipient_needs,
        "routes": routes,
        "profile_count": len(profiles),
    }


# =========================================================
# RUN REDISTRIBUTION OPTIMIZATION
# =========================================================


def run_redistribution_optimization(
    *,
    user,
    medicine_ids=None,
    amc_months=3,
    maximum_distance_km=None,
    vehicle_capacity_units=1,
    max_active_routes=None,
    max_solver_seconds=30,
):
    """
    Build inputs, run OR-Tools, and persist the optimization result.

    Does not reserve or move inventory.

    The optimization run is created outside the allocation
    transaction so that failed runs remain recorded.

    Allocation records and successful run metrics are saved
    together in a separate atomic transaction.
    """

    # -------------------------------------------------
    # 0. Create optimization run outside the allocation
    #    transaction.
    # -------------------------------------------------

    run = RedistributionOptimizationRun.objects.create(
        generated_by=user,
        status=OptimizationRunStatus.PENDING,
        algorithm_version="ortools-cp-sat-v1",
    )

    try:

        # -------------------------------------------------
        # 1. Build optimization inputs
        # -------------------------------------------------

        inputs = build_optimization_inputs(
            user=user,
            medicine_ids=medicine_ids,
            amc_months=amc_months,
            maximum_distance_km=maximum_distance_km,
        )

        run.input_snapshot = {
            "medicine_ids": (
                [str(value) for value in medicine_ids]
                if medicine_ids
                else []
            ),
            "amc_months": amc_months,
            "maximum_distance_km": (
                str(maximum_distance_km)
                if maximum_distance_km is not None
                else None
            ),
            "vehicle_capacity_units": str(vehicle_capacity_units),
            "max_active_routes": max_active_routes,
            "candidate_donor_batches": len(inputs["donor_batches"]),
            "recipient_needs": len(inputs["recipient_needs"]),
            "candidate_routes": len(inputs["routes"]),
        }

        # -------------------------------------------------
        # 2. Check feasible input candidates
        # -------------------------------------------------

        if (
            not inputs["donor_batches"]
            or not inputs["recipient_needs"]
            or not inputs["routes"]
        ):
            run.status = OptimizationRunStatus.INFEASIBLE
            run.solver_status = "NO_FEASIBLE_CANDIDATES"
            run.completed_at = timezone.now()

            run.save()

            return run

        # -------------------------------------------------
        # 3. Execute OR-Tools optimization
        # -------------------------------------------------

        result = optimize_redistribution(
            donor_batches=inputs["donor_batches"],
            recipient_needs=inputs["recipient_needs"],
            routes=inputs["routes"],
            vehicle_capacity_units=vehicle_capacity_units,
            max_active_routes=max_active_routes,
            max_solver_seconds=max_solver_seconds,
        )

        # -------------------------------------------------
        # 3.1 Save solver results in memory
        # -------------------------------------------------

        run.solver_runtime_seconds = Decimal(
            str(
                result["solver_statistics"].get(
                    "wall_time",
                    0,
                )
            )
        )

        run.solver_status = result["status"]

        run.solver_metadata = result["solver_statistics"]

        run.objective_value = (
            int(round(result["objective_value"]))
            if result["objective_value"] is not None
            else None
        )

        # -------------------------------------------------
        # 4. Handle unsuccessful optimization
        # -------------------------------------------------

        if result["status"] not in ["OPTIMAL", "FEASIBLE"]:

            run.status = OptimizationRunStatus.INFEASIBLE
            run.completed_at = timezone.now()

            run.save()

            return run

        # -------------------------------------------------
        # 5. Persist allocations and successful metrics
        #    in one atomic transaction.
        # -------------------------------------------------

        with transaction.atomic():

            total_capacity = ZERO
            total_distance = ZERO

            used_routes = set()

            # -------------------------------------------------
            # 5.1 Create optimization allocation records
            # -------------------------------------------------

            for allocation in result["allocations"]:

                batch = StockBatch.objects.select_related(
                    "warehouse",
                    "warehouse__facility",
                ).get(pk=allocation["batch_id"])

                donor = Facility.objects.get(
                    pk=allocation["donor_id"]
                )

                recipient = Facility.objects.get(
                    pk=allocation["recipient_id"]
                )

                medicine = Medicine.objects.get(
                    pk=allocation["medicine_id"]
                )

                quantity = Decimal(allocation["quantity"])

                capacity = Decimal(allocation["capacity_units"])

                distance = Decimal(allocation["distance_km"])

                RedistributionOptimizationAllocation.objects.create(
                    optimization_run=run,
                    medicine=medicine,
                    donor_facility=donor,
                    recipient_facility=recipient,
                    batch=batch,
                    quantity=quantity,
                    unit_code=next(
                        item["unit_code"]
                        for item in inputs["donor_batches"]
                        if item["batch_id"] == allocation["batch_id"]
                    ),
                    transport_capacity_units=capacity,
                    distance_km=distance,
                    estimated_transport_cost=ZERO,
                    explanation={
                        "priority": allocation["priority"],
                        "solver_status": result["status"],
                        "algorithm_version": "ortools-cp-sat-v1",
                        "stock_reserved": False,
                        "inventory_changed": False,
                    },
                )

                total_capacity += capacity

                route_key = (
                    allocation["donor_id"],
                    allocation["recipient_id"],
                )

                if route_key not in used_routes:
                    total_distance += distance
                    used_routes.add(route_key)

            # -------------------------------------------------
            # 6. Calculate unmet recipient shortage
            # -------------------------------------------------

            allocated_by_recipient_medicine = {}

            for allocation in result["allocations"]:

                key = (
                    allocation["recipient_id"],
                    allocation["medicine_id"],
                )

                allocated_by_recipient_medicine[key] = (
                    allocated_by_recipient_medicine.get(key, ZERO)
                    + Decimal(allocation["quantity"])
                )

            unmet_shortage = ZERO

            for need in inputs["recipient_needs"]:

                key = (
                    need["recipient_id"],
                    need["medicine_id"],
                )

                original_shortage = Decimal(
                    need["shortage_quantity"]
                )

                allocated_quantity = (
                    allocated_by_recipient_medicine.get(key, ZERO)
                )

                unmet_shortage += max(
                    original_shortage - allocated_quantity,
                    ZERO,
                )

            # -------------------------------------------------
            # 7. Save successful optimization metrics
            # -------------------------------------------------

            run.total_unmet_shortage_units = unmet_shortage

            run.total_allocated_capacity_units = total_capacity

            run.total_distance_km = total_distance

            run.total_estimated_transport_cost = ZERO

            run.status = OptimizationRunStatus.COMPLETED

            run.completed_at = timezone.now()

            run.save()

        # The transaction has committed successfully.
        return run

    # -----------------------------------------------------
    # 8. Handle unexpected errors OUTSIDE the allocation
    #    transaction.
    # -----------------------------------------------------

    except Exception as exc:

        run.status = OptimizationRunStatus.FAILED

        run.error_message = str(exc)

        run.completed_at = timezone.now()

        run.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
            ]
        )

        raise
