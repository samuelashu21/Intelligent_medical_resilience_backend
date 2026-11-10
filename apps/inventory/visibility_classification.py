from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.inventory.models import StockPolicy

from apps.inventory.visibility_services import (
    get_facility_medicine_availability,
)


def get_active_stock_policy(
    *,
    facility_id,
    medicine_id,
):
    today = timezone.localdate()

    # ------------------------------------------------------
    # 1. Check facility-specific active stock policy
    # ------------------------------------------------------

    facility_policy = (
        StockPolicy.objects.filter(
            facility_id=facility_id,
            medicine_id=medicine_id,
            status="ACTIVE",
            effective_from__lte=today,
        )
        .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=today))
        .order_by("-effective_from")
        .first()
    )

    if facility_policy:
        return facility_policy

    # ------------------------------------------------------
    # 2. Resolve facility organization
    # ------------------------------------------------------

    facility = (
        __import__(
            "apps.facilities.models",
            fromlist=["Facility"],
        )
        .Facility.objects.select_related("organization")
        .get(pk=facility_id)
    )

    # ------------------------------------------------------
    # 3. Fall back to organization-level stock policy
    # ------------------------------------------------------

    organization_policy = (
        StockPolicy.objects.filter(
            organization_id=facility.organization_id,
            facility__isnull=True,
            medicine_id=medicine_id,
            status="ACTIVE",
            effective_from__lte=today,
        )
        .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=today))
        .order_by("-effective_from")
        .first()
    )

    return organization_policy


def classify_facility_medicine_stock(
    *,
    facility_id,
    medicine_id,
):
    # ------------------------------------------------------
    # 1. Retrieve facility medicine availability
    # ------------------------------------------------------

    stock = get_facility_medicine_availability(
        facility_id=facility_id,
        medicine_id=medicine_id,
    )

    # ------------------------------------------------------
    # 2. Retrieve applicable active stock policy
    # ------------------------------------------------------

    policy = get_active_stock_policy(
        facility_id=facility_id,
        medicine_id=medicine_id,
    )

    available = Decimal(stock["available"])

    # ------------------------------------------------------
    # 3. Handle missing stock policy
    # ------------------------------------------------------

    if not policy:
        return {
            **stock,
            "status": "POLICY_NOT_CONFIGURED",
            "minimum_stock": None,
            "maximum_stock": None,
            "surplus_quantity": Decimal("0"),
            "shortage_quantity": Decimal("0"),
            "policy_configured": False,
        }

    # ------------------------------------------------------
    # 4. Calculate stock thresholds
    # ------------------------------------------------------

    minimum_stock = Decimal(policy.minimum_stock)
    maximum_stock = Decimal(policy.maximum_stock)

    shortage = max(
        minimum_stock - available,
        Decimal("0"),
    )

    surplus = max(
        available - maximum_stock,
        Decimal("0"),
    )

    # ------------------------------------------------------
    # 5. Classify stock availability
    # ------------------------------------------------------

    if available <= 0:
        stock_status = "OUT_OF_STOCK"

    elif available < minimum_stock:
        stock_status = "LOW_STOCK"

    elif available > maximum_stock:
        stock_status = "SURPLUS"

    else:
        stock_status = "ADEQUATE"

    # ------------------------------------------------------
    # 6. Return classified stock information
    # ------------------------------------------------------

    return {
        **stock,
        "status": stock_status,
        "minimum_stock": minimum_stock,
        "maximum_stock": maximum_stock,
        "surplus_quantity": surplus,
        "shortage_quantity": shortage,
        "policy_configured": True,
    }
