from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
    StockPolicy,
)

from apps.consumption.models import DailyConsumption

ZERO = Decimal("0")


def calculate_amc(
    facility_id,
    medicine_id,
    months=3,
    as_of=None,
):
    """
    Calculate average monthly consumption from completed
    calendar months only.

    Missing consumption records are treated as zero in this
    initial calculation. Reporting completeness must be
    considered before activating a policy.
    """
    if not 1 <= months <= 24:
        raise ValidationError("AMC period must be between 1 and 24 months.")

    as_of = as_of or timezone.localdate()

    year = as_of.year
    month = as_of.month - 1

    if month == 0:
        month = 12
        year -= 1

    monthly_totals = []

    for _ in range(months):
        result = DailyConsumption.objects.filter(
            facility_id=facility_id,
            medicine_id=medicine_id,
            consumption_date__year=year,
            consumption_date__month=month,
        ).values_list("quantity", flat=True)

        monthly_total = sum(result, ZERO)
        monthly_totals.append(monthly_total)

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    total = sum(monthly_totals, ZERO)

    return {
        "amc": total / Decimal(months),
        "total_consumption": total,
        "months_included": months,
        "monthly_totals": monthly_totals,
    }


def calculate_daily_demand(amc):
    """
    Convert average monthly consumption to average daily demand
    using a 30-day planning month.
    """
    return Decimal(amc) / Decimal("30")


def calculate_reorder_point(
    daily_demand,
    lead_time_days,
    safety_stock,
):
    return Decimal(daily_demand) * Decimal(lead_time_days) + Decimal(safety_stock)


def calculate_target_stock(
    daily_demand,
    lead_time_days,
    review_period_days,
    safety_stock,
):
    return Decimal(daily_demand) * Decimal(
        lead_time_days + review_period_days
    ) + Decimal(safety_stock)


def get_usable_stock(facility_id, medicine_id):
    """
    Sum available stock in warehouses directly associated
    with the facility.

    Expired stock is excluded.
    """
    today = timezone.localdate()

    balances = InventoryBalance.objects.filter(
        batch__medicine_id=medicine_id,
        batch__warehouse__facility_id=facility_id,
    ).select_related("batch")

    total = ZERO

    for balance in balances:
        expiry_date = balance.batch.expiry_date

        if expiry_date and expiry_date < today:
            continue

        available = balance.quantity_on_hand - balance.quantity_reserved

        total += max(ZERO, available)

    return total


def get_active_stock_policy(
    facility_id,
    medicine_id,
    as_of=None,
):
    """
    Facility policy takes precedence over organization default.
    """
    as_of = as_of or timezone.localdate()

    facility_policy = (
        StockPolicy.objects.filter(
            facility_id=facility_id,
            medicine_id=medicine_id,
            status=StockPolicy.PolicyStatus.ACTIVE,
            effective_from__lte=as_of,
        )
        .filter(models_q_effective_until(as_of))
        .first()
    )

    if facility_policy:
        return facility_policy

    from apps.facilities.models import Facility

    facility = Facility.objects.select_related("organization").get(pk=facility_id)

    return (
        StockPolicy.objects.filter(
            facility__isnull=True,
            organization_id=facility.organization_id,
            medicine_id=medicine_id,
            status=StockPolicy.PolicyStatus.ACTIVE,
            effective_from__lte=as_of,
        )
        .filter(models_q_effective_until(as_of))
        .first()
    )


def models_q_effective_until(as_of):
    from django.db.models import Q

    return Q(effective_until__isnull=True) | Q(effective_until__gte=as_of)


def evaluate_stock_policy(
    facility_id,
    medicine_id,
    policy=None,
):
    """
    Evaluate inventory against the effective policy.
    Does not modify inventory or create a replenishment request.
    """
    policy = policy or get_active_stock_policy(
        facility_id,
        medicine_id,
    )

    if not policy:
        return {
            "policy_configured": False,
            "facility_id": str(facility_id),
            "medicine_id": str(medicine_id),
            "status": "POLICY_MISSING",
            "message": "No active stock policy exists.",
        }

    consumption = calculate_amc(
        facility_id,
        medicine_id,
    )

    amc = consumption["amc"]
    daily_demand = calculate_daily_demand(amc)

    usable_stock = get_usable_stock(
        facility_id,
        medicine_id,
    )

    reorder_point = calculate_reorder_point(
        daily_demand,
        policy.lead_time_days,
        policy.safety_stock,
    )

    calculated_target = calculate_target_stock(
        daily_demand,
        policy.lead_time_days,
        policy.review_period_days,
        policy.safety_stock,
    )

    target_stock = min(
        policy.maximum_stock,
        max(policy.minimum_stock, calculated_target),
    )

    if usable_stock <= ZERO:
        status = "STOCKOUT"
    elif usable_stock <= policy.minimum_stock:
        status = "BELOW_MINIMUM"
    elif usable_stock <= reorder_point:
        status = "REORDER_REQUIRED"
    elif usable_stock > policy.maximum_stock:
        status = "ABOVE_MAXIMUM"
    else:
        status = "ADEQUATE"

    recommended_quantity = max(
        ZERO,
        target_stock - usable_stock,
    )

    if (
        recommended_quantity > ZERO
        and policy.minimum_order_quantity > ZERO
        and recommended_quantity < policy.minimum_order_quantity
    ):
        recommended_quantity = policy.minimum_order_quantity

    return {
        "policy_configured": True,
        "policy_id": str(policy.pk),
        "policy_level": policy.policy_level,
        "facility_id": str(facility_id),
        "medicine_id": str(medicine_id),
        "status": status,
        "on_hand_available": str(usable_stock),
        "amc": str(amc),
        "daily_demand": str(daily_demand),
        "lead_time_days": policy.lead_time_days,
        "review_period_days": policy.review_period_days,
        "minimum_stock": str(policy.minimum_stock),
        "maximum_stock": str(policy.maximum_stock),
        "safety_stock": str(policy.safety_stock),
        "buffer_stock": str(policy.buffer_stock),
        "reorder_point": str(reorder_point),
        "calculated_target_stock": str(calculated_target),
        "target_stock": str(target_stock),
        "recommended_quantity": str(recommended_quantity),
        "months_of_stock": (str(usable_stock / amc) if amc > ZERO else None),
        "amc_months_included": consumption["months_included"],
        "message": (
            "Policy evaluation completed. "
            "Review the recommendation before creating a request."
        ),
    }


@transaction.atomic
def activate_stock_policy(policy_id, user):
    policy = StockPolicy.objects.select_for_update().get(pk=policy_id)

    if policy.effective_until and (policy.effective_until < timezone.localdate()):
        raise ValidationError("An expired policy cannot be activated.")

    policy.status = StockPolicy.PolicyStatus.ACTIVE
    policy.updated_by = user
    policy.save()

    return policy


@transaction.atomic
def deactivate_stock_policy(policy_id, user):
    policy = StockPolicy.objects.select_for_update().get(pk=policy_id)

    policy.status = StockPolicy.PolicyStatus.INACTIVE
    policy.updated_by = user
    policy.save()

    return policy
