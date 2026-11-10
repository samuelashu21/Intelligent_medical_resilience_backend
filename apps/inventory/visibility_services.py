from decimal import Decimal

from django.db.models import (
    Sum,
    F,
    Q,
    Value,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
)

from apps.facilities.models import Facility

from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
)

ZERO = Decimal("0")


def get_facility_stock_queryset(
    *,
    medicine_id=None,
    facility_ids=None,
    organization_ids=None,
    include_zero=False,
):
    """
    Return eligible stock balances for authorized facilities.

    Expired batches and inactive facilities/warehouses
    are excluded.
    """

    today = timezone.localdate()

    queryset = InventoryBalance.objects.filter(
        batch__expiry_date__gte=today,
        batch__warehouse__is_active=True,
        batch__warehouse__facility__is_active=True,
    ).select_related(
        "batch",
        "batch__medicine",
        "batch__warehouse",
        "batch__warehouse__facility",
        "batch__warehouse__organization",
    )

    if medicine_id:
        queryset = queryset.filter(batch__medicine_id=medicine_id)

    if facility_ids is not None:
        queryset = queryset.filter(batch__warehouse__facility_id__in=facility_ids)

    if organization_ids is not None:
        queryset = queryset.filter(
            batch__warehouse__organization_id__in=organization_ids
        )

    if not include_zero:
        queryset = queryset.filter(quantity_on_hand__gt=ZERO)

    return queryset


def get_facility_medicine_stock(
    *,
    medicine_id,
    facility_ids=None,
    organization_ids=None,
):
    """
    Aggregate eligible stock at facility level.

    Available quantity is computed as on-hand minus reserved.
    """

    queryset = get_facility_stock_queryset(
        medicine_id=medicine_id,
        facility_ids=facility_ids,
        organization_ids=organization_ids,
    )

    available_expression = ExpressionWrapper(
        F("quantity_on_hand") - F("quantity_reserved"),
        output_field=DecimalField(
            max_digits=20,
            decimal_places=3,
        ),
    )

    return (
        queryset.values(
            medicine_id=F("batch__medicine_id"),
            medicine_code=F("batch__medicine__code"),
            medicine_name=F("batch__medicine__generic_name"),
            facility_id=F("batch__warehouse__facility_id"),
            facility_code=F("batch__warehouse__facility__code"),
            facility_name=F("batch__warehouse__facility__name"),
            organization_id=F("batch__warehouse__facility__organization_id"),
            organization_name=F("batch__warehouse__facility__organization__name"),
        )
        .annotate(
            on_hand=Coalesce(
                Sum("quantity_on_hand"),
                Value(ZERO),
            ),
            reserved=Coalesce(
                Sum("quantity_reserved"),
                Value(ZERO),
            ),
            available=Coalesce(
                Sum(available_expression),
                Value(ZERO),
            ),
        )
        .order_by("facility_name")
    )


def get_facility_stock_summary(
    *,
    facility_id,
    medicine_id=None,
):
    """
    Return a facility's eligible stock summary.
    """

    queryset = get_facility_stock_queryset(
        medicine_id=medicine_id,
        facility_ids=[facility_id],
    )

    summary = queryset.aggregate(
        on_hand=Coalesce(
            Sum("quantity_on_hand"),
            Value(ZERO),
        ),
        reserved=Coalesce(
            Sum("quantity_reserved"),
            Value(ZERO),
        ),
    )

    on_hand = summary["on_hand"] or ZERO
    reserved = summary["reserved"] or ZERO

    return {
        "facility_id": str(facility_id),
        "on_hand": on_hand,
        "reserved": reserved,
        "available": max(on_hand - reserved, ZERO),
    }


def get_facility_medicine_availability(
    *,
    facility_id,
    medicine_id,
):
    """
    Return eligible stock at a specific facility for one medicine.
    """

    rows = get_facility_stock_queryset(
        medicine_id=medicine_id,
        facility_ids=[facility_id],
    )

    result = rows.aggregate(
        on_hand=Coalesce(
            Sum("quantity_on_hand"),
            Value(ZERO),
        ),
        reserved=Coalesce(
            Sum("quantity_reserved"),
            Value(ZERO),
        ),
    )

    on_hand = result["on_hand"] or ZERO
    reserved = result["reserved"] or ZERO

    return {
        "facility_id": str(facility_id),
        "medicine_id": str(medicine_id),
        "on_hand": on_hand,
        "reserved": reserved,
        "available": max(on_hand - reserved, ZERO),
    }


def get_facility_stock_by_medicine(
    *,
    facility_id,
):
    """
    Return the stock portfolio for one facility.
    """

    queryset = get_facility_stock_queryset(
        facility_ids=[facility_id],
    )

    return (
        queryset.values(
            "batch__medicine_id",
            "batch__medicine__code",
            "batch__medicine__generic_name",
        )
        .annotate(
            on_hand=Coalesce(
                Sum("quantity_on_hand"),
                Value(ZERO),
            ),
            reserved=Coalesce(
                Sum("quantity_reserved"),
                Value(ZERO),
            ),
        )
        .order_by("batch__medicine__generic_name")
    )


def get_visible_facility_ids(user):
    """
    Resolve facilities visible to a user.

    Superusers have global visibility. Other users receive
    only facility IDs granted by their active role assignments.
    """

    if user.is_superuser:
        return Facility.objects.filter(is_active=True).values_list("id", flat=True)

    return get_user_accessible_facility_ids(
        user,
        permission_code="inventory.visibility.view",
    )


def get_visible_facility_stock(
    *,
    user,
    medicine_id=None,
):
    facility_ids = get_visible_facility_ids(user)

    return get_facility_stock_queryset(
        medicine_id=medicine_id,
        facility_ids=facility_ids,
    )


def get_visible_facility_medicine_stock(
    *,
    user,
    medicine_id,
):
    facility_ids = get_visible_facility_ids(user)

    return get_facility_medicine_stock(
        medicine_id=medicine_id,
        facility_ids=facility_ids,
    )
