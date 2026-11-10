from decimal import Decimal, ROUND_DOWN
from math import radians, sin, cos, sqrt, atan2
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    Sum,
    F,
    Value,
    DecimalField,
    Q,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
)

from apps.consumption.services import (
    calculate_average_monthly_consumption,
)

from apps.facilities.models import Facility

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
    StockPolicy,
)

from apps.medicines.models import Medicine

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
    RecommendationStatus,
    RecommendationPriority,
)

ZERO = Decimal("0")
ONE = Decimal("1")
THIRTY = Decimal("30")


def decimal_value(value):
    if value is None:
        return ZERO
    return Decimal(str(value))


def calculate_daily_demand(
    *,
    facility_id,
    medicine_id,
    months=3,
):
    """
    Calculate daily demand from completed-month AMC.

    Returns None when no historical consumption is available.
    """

    result = calculate_average_monthly_consumption(
        facility_id=facility_id,
        medicine_id=medicine_id,
        number_of_months=months,
    )

    average = decimal_value(result.get("average"))

    months_included = result.get(
        "months_included",
        0,
    )

    if months_included <= 0:
        return None

    if average <= ZERO:
        return ZERO

    return average / THIRTY


def calculate_stock_coverage_days(
    *,
    available,
    daily_demand,
):
    if daily_demand is None:
        return None

    if daily_demand <= ZERO:
        return None

    return (decimal_value(available) / daily_demand).quantize(Decimal("0.01"))


def get_effective_stock_policy(
    *,
    facility,
    medicine_id,
):
    """
    Resolve facility-specific policy first,
    then organization default.

    Include policies that have no expiration date
    or whose expiration date is today or in the future.
    """

    today = timezone.localdate()

    active = StockPolicy.objects.filter(
        medicine_id=medicine_id,
        status="ACTIVE",
        effective_from__lte=today,
    ).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=today))

    # Facility-specific policy takes precedence.
    facility_policy = (
        active.filter(
            facility=facility,
        )
        .order_by("-effective_from")
        .first()
    )

    if facility_policy:
        return facility_policy

    # Fall back to organization-wide default policy.
    return (
        active.filter(
            facility__isnull=True,
            organization=facility.organization,
        )
        .order_by("-effective_from")
        .first()
    )


def get_facility_eligible_stock(
    *,
    facility_id,
    medicine_id,
):
    """
    Return non-expired stock by batch, ordered FEFO.

    Only unreserved stock is considered.
    """

    today = timezone.localdate()

    available_expression = F("quantity_on_hand") - F("quantity_reserved")

    queryset = (
        InventoryBalance.objects.filter(
            batch__medicine_id=medicine_id,
            batch__warehouse__facility_id=facility_id,
            batch__warehouse__is_active=True,
            batch__expiry_date__gte=today,
        )
        .annotate(available_quantity=available_expression)
        .filter(available_quantity__gt=ZERO)
        .select_related(
            "batch",
            "batch__warehouse",
        )
        .order_by(
            "batch__expiry_date",
            "batch__manufacture_date",
            "batch__batch_number",
        )
    )

    return queryset


def get_facility_available_quantity(
    *,
    facility_id,
    medicine_id,
):
    balances = get_facility_eligible_stock(
        facility_id=facility_id,
        medicine_id=medicine_id,
    )

    result = balances.aggregate(
        available=Coalesce(
            Sum("available_quantity"),
            Value(ZERO),
            output_field=DecimalField(
                max_digits=20,
                decimal_places=3,
            ),
        )
    )

    return decimal_value(result["available"])


def get_facility_stock_profile(
    *,
    facility,
    medicine_id,
    amc_months=3,
):
    """
    Combine eligible stock, demand, and policy information.
    """

    available = get_facility_available_quantity(
        facility_id=facility.pk,
        medicine_id=medicine_id,
    )

    daily_demand = calculate_daily_demand(
        facility_id=facility.pk,
        medicine_id=medicine_id,
        months=amc_months,
    )

    policy = get_effective_stock_policy(
        facility=facility,
        medicine_id=medicine_id,
    )

    if policy:
        minimum_stock = decimal_value(policy.minimum_stock)
        maximum_stock = decimal_value(policy.maximum_stock)
        safety_stock = decimal_value(policy.safety_stock)
    else:
        minimum_stock = None
        maximum_stock = None
        safety_stock = None

    coverage = calculate_stock_coverage_days(
        available=available,
        daily_demand=daily_demand,
    )

    return {
        "facility": facility,
        "medicine_id": medicine_id,
        "available": available,
        "daily_demand": daily_demand,
        "coverage_days": coverage,
        "minimum_stock": minimum_stock,
        "maximum_stock": maximum_stock,
        "safety_stock": safety_stock,
        "policy_configured": policy is not None,
        "policy": policy,
    }


def calculate_operational_target(profile):
    """
    Calculate a demand-aware stock target.

    Use the greater of the configured minimum stock and
    the demand-based lead-time/review-period target.
    """

    if not profile["policy_configured"]:
        return None

    policy = profile["policy"]

    minimum_stock = profile["minimum_stock"]
    safety_stock = profile["safety_stock"] or ZERO

    daily_demand = profile["daily_demand"]

    if daily_demand is None:
        return minimum_stock

    lead_time = Decimal(str(policy.lead_time_days))

    review_period = Decimal(str(policy.review_period_days))

    demand_target = (daily_demand * (lead_time + review_period)) + safety_stock

    return max(
        minimum_stock,
        demand_target,
    )


def calculate_donor_transferable_quantity(profile):
    """
    Calculate stock that a donor can safely offer.

    Keep enough stock for its own operational target.
    """

    if not profile["policy_configured"]:
        return ZERO

    target = calculate_operational_target(profile)

    if target is None:
        return ZERO

    surplus = max(
        profile["available"] - target,
        ZERO,
    )

    return surplus.quantize(
        Decimal("0.001"),
        rounding=ROUND_DOWN,
    )


def calculate_recipient_shortage(profile):
    """
    Calculate the recipient's replenishment requirement.
    """

    if not profile["policy_configured"]:
        return ZERO

    target = calculate_operational_target(profile)

    if target is None:
        return ZERO

    shortage = max(
        target - profile["available"],
        ZERO,
    )

    return shortage.quantize(
        Decimal("0.001"),
        rounding=ROUND_DOWN,
    )


def calculate_haversine_distance(
    *,
    latitude_a,
    longitude_a,
    latitude_b,
    longitude_b,
):
    """
    Calculate straight-line geographic distance in kilometres.

    This is not a road travel distance.
    """

    if any(
        value is None
        for value in [
            latitude_a,
            longitude_a,
            latitude_b,
            longitude_b,
        ]
    ):
        return None

    lat1 = radians(float(latitude_a))
    lon1 = radians(float(longitude_a))
    lat2 = radians(float(latitude_b))
    lon2 = radians(float(longitude_b))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    earth_radius_km = 6371.0

    return Decimal(str(earth_radius_km * c)).quantize(Decimal("0.01"))


def get_facility_distance(donor, recipient):
    """
    Use facility coordinates where available.
    """

    return calculate_haversine_distance(
        latitude_a=donor.latitude,
        longitude_a=donor.longitude,
        latitude_b=recipient.latitude,
        longitude_b=recipient.longitude,
    )


# ==========================================================
# FEFO BATCH ALLOCATION
# ==========================================================


def allocate_donor_batches_fefo(
    *,
    donor_facility_id,
    medicine_id,
    requested_quantity,
    recipient_daily_demand=None,
    remaining_by_batch=None,
):
    """
    Allocate donor batches in FEFO order without changing inventory.

    The returned allocations are recommendations only.

    remaining_by_batch is a shared dictionary used to prevent
    the same batch quantity from being allocated repeatedly
    during one recommendation-generation run.
    """

    today = timezone.localdate()

    remaining = decimal_value(requested_quantity)

    allocations = []

    if remaining_by_batch is None:
        remaining_by_batch = {}

    balances = get_facility_eligible_stock(
        facility_id=donor_facility_id,
        medicine_id=medicine_id,
    )

    for balance in balances:

        if remaining <= ZERO:
            break

        batch = balance.batch
        batch_id = str(batch.pk)

        database_available = max(
            decimal_value(balance.quantity_on_hand)
            - decimal_value(balance.quantity_reserved),
            ZERO,
        )

        batch_available = decimal_value(
            remaining_by_batch.get(
                batch_id,
                database_available,
            )
        )

        expiry_days = (batch.expiry_date - today).days

        if batch_available <= ZERO:
            continue

        if (
            recipient_daily_demand is not None
            and decimal_value(recipient_daily_demand) > ZERO
        ):
            consumption_days = remaining / decimal_value(recipient_daily_demand)

            if Decimal(expiry_days) < consumption_days:
                continue

        allocated = min(
            batch_available,
            remaining,
        )

        allocations.append(
            {
                "batch_id": batch_id,
                "batch_number": batch.batch_number,
                "expiry_date": batch.expiry_date.isoformat(),
                "expiry_days_remaining": expiry_days,
                "quantity": str(allocated),
            }
        )

        # Update the shared batch balance.
        remaining_by_batch[batch_id] = batch_available - allocated

        remaining -= allocated

    allocated_total = decimal_value(requested_quantity) - remaining

    return {
        "allocations": allocations,
        "allocated_quantity": allocated_total,
        "unallocated_quantity": remaining,
    }


def calculate_recommendation_priority(
    *,
    recipient_profile,
    distance_km,
    essential_medicine=False,
):
    """
    Produce a transparent 0–100 priority score.

    The score is a ranking heuristic, not a clinically
    validated stockout probability.
    """

    coverage = recipient_profile["coverage_days"]

    if coverage is None:
        urgency_score = 20
    elif coverage <= 3:
        urgency_score = 40
    elif coverage <= 7:
        urgency_score = 32
    elif coverage <= 14:
        urgency_score = 22
    elif coverage <= 30:
        urgency_score = 12
    else:
        urgency_score = 0

    shortage = calculate_recipient_shortage(recipient_profile)

    available = recipient_profile["available"]

    if shortage > ZERO:
        need_score = min(
            float(
                shortage
                / max(
                    available + shortage,
                    ONE,
                )
            )
            * 25,
            25,
        )
    else:
        need_score = 0

    essential_score = 15 if essential_medicine else 0

    if distance_km is None:
        distance_score = 3
    elif distance_km <= 25:
        distance_score = 10
    elif distance_km <= 75:
        distance_score = 7
    elif distance_km <= 150:
        distance_score = 4
    else:
        distance_score = 1

    total = min(
        urgency_score + need_score + essential_score + distance_score,
        100,
    )

    if coverage is not None and coverage <= 3:
        priority = RecommendationPriority.CRITICAL
    elif total >= 65:
        priority = RecommendationPriority.HIGH
    elif total >= 35:
        priority = RecommendationPriority.NORMAL
    else:
        priority = RecommendationPriority.LOW

    return {
        "score": Decimal(str(round(total, 2))),
        "priority": priority,
        "components": {
            "urgency": urgency_score,
            "need": round(need_score, 2),
            "essential_medicine": essential_score,
            "distance": distance_score,
        },
    }


def get_visible_facilities_for_recommendations(
    user,
    permission_code="redistribution.recommendation.view",
):
    if user.is_superuser:
        return Facility.objects.filter(
            is_active=True
        ).select_related("organization")

    visible_ids = get_user_accessible_facility_ids(
        user,
        permission_code=permission_code,
    )

    return Facility.objects.filter(
        id__in=visible_ids,
        is_active=True,
    ).select_related("organization")


def get_medicine_essential_status(medicine):
    """
    Support installations where the essential-medicine flag
    may have a different name or may not yet exist.
    """

    return bool(
        getattr(
            medicine,
            "is_essential",
            False,
        )
    )


def get_recommendation_unit(medicine):
    """
    Return the medicine's configured inventory unit.
    """

    return (
        getattr(medicine, "unit_code", None)
        or getattr(medicine, "base_unit", None)
        or "UNIT"
    )


# ==========================================================
# GENERATE REDISTRIBUTION RECOMMENDATIONS
# ==========================================================


@transaction.atomic
def generate_redistribution_recommendations(
    *,
    user,
    medicine_id,
    amc_months=3,
    maximum_distance_km=None,
):
    """
    Generate recommendations for one medicine.

    No stock is reserved, issued, or transferred.

    Shared FEFO batch balances prevent duplicate batch
    allocations across recipients in this generation run.

    Existing unexpired pending recommendations for the same
    medicine and facility pair are not duplicated.
    """

    medicine = Medicine.objects.filter(pk=medicine_id).first()

    if medicine is None:
        raise ValidationError("Medicine not found.")

    facilities = list(get_visible_facilities_for_recommendations(user))

    if len(facilities) < 2:
        return []

    profiles = {}

    for facility in facilities:

        profile = get_facility_stock_profile(
            facility=facility,
            medicine_id=medicine.pk,
            amc_months=amc_months,
        )

        # A policy and demand history are required for safe matching.
        if not profile["policy_configured"] or profile["daily_demand"] is None:
            continue

        profiles[facility.pk] = profile

    donors = []
    recipients = []

    for facility in facilities:

        profile = profiles.get(facility.pk)

        if not profile:
            continue

        transferable = calculate_donor_transferable_quantity(profile)

        shortage = calculate_recipient_shortage(profile)

        if transferable > ZERO:
            donors.append(
                {
                    "facility": facility,
                    "profile": profile,
                    "remaining": transferable,
                }
            )

        if shortage > ZERO:
            recipients.append(
                {
                    "facility": facility,
                    "profile": profile,
                    "remaining": shortage,
                }
            )

    if not donors or not recipients:
        return []

    # ------------------------------------------------------
    # Initialize shared FEFO batch quantities once per donor.
    # ------------------------------------------------------

    donor_batch_remaining = {donor["facility"].pk: {} for donor in donors}

    essential = get_medicine_essential_status(medicine)

    # Prioritize recipients with the lowest coverage first.
    recipients.sort(
        key=lambda item: (
            item["profile"]["coverage_days"]
            if item["profile"]["coverage_days"] is not None
            else Decimal("999999")
        )
    )

    recommendations = []

    # Match each recipient to the nearest eligible donor first.
    for recipient in recipients:

        recipient_facility = recipient["facility"]
        recipient_profile = recipient["profile"]

        if recipient["remaining"] <= ZERO:
            continue

        donor_candidates = []

        for donor in donors:

            if donor["remaining"] <= ZERO:
                continue

            donor_facility = donor["facility"]

            if donor_facility.pk == recipient_facility.pk:
                continue

            distance = get_facility_distance(
                donor_facility,
                recipient_facility,
            )

            if (
                maximum_distance_km is not None
                and distance is not None
                and distance > Decimal(str(maximum_distance_km))
            ):
                continue

            donor_candidates.append(
                {
                    "donor": donor,
                    "distance": distance,
                }
            )

        donor_candidates.sort(
            key=lambda item: (
                item["distance"] if item["distance"] is not None else Decimal("999999")
            )
        )

        for candidate in donor_candidates:

            donor = candidate["donor"]
            donor_facility = donor["facility"]
            donor_profile = donor["profile"]

            if donor["remaining"] <= ZERO or recipient["remaining"] <= ZERO:
                continue

            # --------------------------------------------------
            # Prevent duplicate pending recommendations.
            # --------------------------------------------------

            existing = RedistributionRecommendation.objects.filter(
                medicine=medicine,
                donor_facility=donor_facility,
                recipient_facility=recipient_facility,
                status=RecommendationStatus.PENDING,
                expires_at__gt=timezone.now(),
            ).exists()

            if existing:
                continue

            proposed_quantity = min(
                donor["remaining"],
                recipient["remaining"],
            )

            # --------------------------------------------------
            # Allocate using the donor's shared batch dictionary.
            # --------------------------------------------------

            batch_result = allocate_donor_batches_fefo(
                donor_facility_id=donor_facility.pk,
                medicine_id=medicine.pk,
                requested_quantity=proposed_quantity,
                recipient_daily_demand=(recipient_profile["daily_demand"]),
                remaining_by_batch=donor_batch_remaining[donor_facility.pk],
            )

            actual_quantity = batch_result["allocated_quantity"]

            if actual_quantity <= ZERO:
                continue

            # Do not create a recommendation unless the full
            # proposed quantity can be supported by eligible batches.
            if batch_result["unallocated_quantity"] > ZERO:
                continue

            distance = candidate["distance"]

            priority_result = calculate_recommendation_priority(
                recipient_profile=recipient_profile,
                distance_km=distance,
                essential_medicine=essential,
            )

            donor_after = donor_profile["available"] - actual_quantity

            recipient_after = recipient_profile["available"] + actual_quantity

            donor_coverage_after = calculate_stock_coverage_days(
                available=donor_after,
                daily_demand=donor_profile["daily_demand"],
            )

            recipient_coverage_after = calculate_stock_coverage_days(
                available=recipient_after,
                daily_demand=recipient_profile["daily_demand"],
            )

            recommendation = RedistributionRecommendation.objects.create(
                medicine=medicine,
                donor_facility=donor_facility,
                recipient_facility=recipient_facility,
                donor_organization=donor_facility.organization,
                recipient_organization=recipient_facility.organization,
                recommended_quantity=actual_quantity,
                unit_code=get_recommendation_unit(medicine),
                donor_available_before=donor_profile["available"],
                recipient_available_before=recipient_profile["available"],
                donor_available_after=donor_after,
                recipient_available_after=recipient_after,
                donor_coverage_days_before=(donor_profile["coverage_days"]),
                recipient_coverage_days_before=(recipient_profile["coverage_days"]),
                donor_coverage_days_after=donor_coverage_after,
                recipient_coverage_days_after=recipient_coverage_after,
                priority=priority_result["priority"],
                priority_score=priority_result["score"],
                distance_km=distance,
                explanation={
                    "reason": (
                        "Recipient stock is below its operational "
                        "target and donor stock is above its own target."
                    ),
                    "priority_components": (priority_result["components"]),
                    "donor_policy_configured": True,
                    "recipient_policy_configured": True,
                    "batch_allocations": (batch_result["allocations"]),
                    "expiry_aware": True,
                    "distance_method": "haversine_straight_line",
                    "algorithm_version": "redistribution-v1",
                },
                expires_at=(timezone.now() + timedelta(days=2)),
            )

            recommendations.append(recommendation)

            # --------------------------------------------------
            # Update in-memory quantities.
            # --------------------------------------------------

            donor["remaining"] -= actual_quantity
            recipient["remaining"] -= actual_quantity

            donor_profile["available"] -= actual_quantity
            recipient_profile["available"] += actual_quantity

            donor_profile["coverage_days"] = donor_coverage_after

            recipient_profile["coverage_days"] = recipient_coverage_after

    return recommendations
