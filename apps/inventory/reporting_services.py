from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
)

from apps.consumption.models import (
    DailyConsumption,
)

from apps.inventory.reporting_config import (
    DEFAULT_AMC_MONTHS,
    DEFAULT_CRITICAL_COVERAGE_MONTHS,
    DEFAULT_HIGH_COVERAGE_MONTHS,
    DEFAULT_LOW_COVERAGE_MONTHS,
    DEFAULT_NEAR_EXPIRY_DAYS,
    MAX_REPORTING_AMC_MONTHS,
)

ZERO = Decimal("0")


def get_available_quantity(balance):
    expiry_date = balance.batch.expiry_date

    if expiry_date and expiry_date < timezone.localdate():
        return ZERO

    return max(
        ZERO,
        balance.quantity_on_hand - balance.quantity_reserved,
    )


def get_facility_for_warehouse(warehouse):
    """
    Resolve the facility associated with a warehouse.

    This implementation assumes Warehouse.facility exists.
    If your Phase 14 implementation uses a different relationship,
    change this function only.
    """
    return getattr(warehouse, "facility", None)


def get_reporting_balances(
    organization_ids=None,
    facility_id=None,
    medicine_id=None,
):
    """
    Return balances with related batch, medicine, warehouse,
    organization and facility information.
    """
    queryset = InventoryBalance.objects.select_related(
        "batch",
        "batch__medicine",
        "batch__warehouse",
        "batch__warehouse__organization",
    )

    if medicine_id:
        queryset = queryset.filter(batch__medicine_id=medicine_id)

    if organization_ids is not None:
        queryset = queryset.filter(
            batch__warehouse__organization_id__in=organization_ids
        )

    results = []

    for balance in queryset.iterator():
        warehouse = balance.batch.warehouse
        facility = get_facility_for_warehouse(warehouse)

        if facility_id and (not facility or str(facility.pk) != str(facility_id)):
            continue

        results.append((balance, facility))

    return results


def get_facility_stock_summary(
    facility_id,
    organization_ids=None,
):
    balances = get_reporting_balances(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    total_on_hand = ZERO
    total_reserved = ZERO
    total_available = ZERO
    batch_count = 0
    medicine_totals = defaultdict(
        lambda: {
            "on_hand": ZERO,
            "reserved": ZERO,
            "available": ZERO,
            "batches": 0,
        }
    )

    for balance, facility in balances:
        on_hand = balance.quantity_on_hand
        reserved = balance.quantity_reserved
        available = get_available_quantity(balance)

        total_on_hand += on_hand
        total_reserved += reserved
        total_available += available
        batch_count += 1

        medicine = balance.batch.medicine
        item = medicine_totals[str(medicine.pk)]

        item["medicine_id"] = str(medicine.pk)
        item["medicine_code"] = medicine.code
        item["medicine_name"] = medicine.generic_name
        item["on_hand"] += on_hand
        item["reserved"] += reserved
        item["available"] += available
        item["batches"] += 1

    return {
        "facility_id": str(facility_id),
        "total_on_hand": str(total_on_hand),
        "total_reserved": str(total_reserved),
        "total_available": str(total_available),
        "batch_count": batch_count,
        "medicine_count": len(medicine_totals),
        "medicines": [
            {
                **item,
                "on_hand": str(item["on_hand"]),
                "reserved": str(item["reserved"]),
                "available": str(item["available"]),
            }
            for item in medicine_totals.values()
        ],
    }


def get_medicine_stock_status(
    organization_ids=None,
    facility_id=None,
    medicine_id=None,
):
    """
    Calculate stock status per facility and medicine.

    AMC is based on completed calendar months of daily
    consumption records. It includes zero-consumption months.
    """
    balances = get_reporting_balances(
        organization_ids=organization_ids,
        facility_id=facility_id,
        medicine_id=medicine_id,
    )

    grouped = defaultdict(
        lambda: {
            "facility": None,
            "medicine": None,
            "on_hand": ZERO,
            "reserved": ZERO,
            "available": ZERO,
            "batches": 0,
        }
    )

    for balance, facility in balances:
        if not facility:
            continue

        medicine = balance.batch.medicine

        key = (str(facility.pk), str(medicine.pk))
        item = grouped[key]

        item["facility"] = facility
        item["medicine"] = medicine
        item["on_hand"] += balance.quantity_on_hand
        item["reserved"] += balance.quantity_reserved
        item["available"] += get_available_quantity(balance)
        item["batches"] += 1

    today = timezone.localdate()
    rows = []

    for item in grouped.values():
        facility = item["facility"]
        medicine = item["medicine"]

        # Previous three completed calendar months.
        year = today.year
        month = today.month - 1

        if month == 0:
            month = 12
            year -= 1

        monthly_values = []

        for _ in range(DEFAULT_AMC_MONTHS):
            result = DailyConsumption.objects.filter(
                facility=facility,
                medicine=medicine,
                consumption_date__year=year,
                consumption_date__month=month,
            ).aggregate(total=Sum("quantity"))

            monthly_values.append(result["total"] or ZERO)

            month -= 1
            if month == 0:
                month = 12
                year -= 1

        amc = sum(monthly_values, ZERO) / Decimal(DEFAULT_AMC_MONTHS)

        available = item["available"]

        if amc > ZERO:
            coverage = available / amc
        else:
            coverage = None

        if available <= ZERO:
            status = "STOCKOUT"
        elif coverage is None:
            status = "NO_CONSUMPTION_HISTORY"
        elif coverage <= DEFAULT_CRITICAL_COVERAGE_MONTHS:
            status = "CRITICAL"
        elif coverage <= DEFAULT_LOW_COVERAGE_MONTHS:
            status = "LOW"
        elif coverage >= DEFAULT_HIGH_COVERAGE_MONTHS:
            status = "HIGH_COVERAGE"
        else:
            status = "ADEQUATE"

        rows.append(
            {
                "facility_id": str(facility.pk),
                "facility_code": facility.code,
                "facility_name": facility.name,
                "organization_id": str(facility.organization_id),
                "medicine_id": str(medicine.pk),
                "medicine_code": medicine.code,
                "medicine_name": medicine.generic_name,
                "on_hand": str(item["on_hand"]),
                "reserved": str(item["reserved"]),
                "available": str(available),
                "amc": str(amc),
                "months_of_stock": (str(coverage) if coverage is not None else None),
                "batch_count": item["batches"],
                "status": status,
            }
        )

    return rows


def get_stockout_report(organization_ids=None, facility_id=None):
    rows = get_medicine_stock_status(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    return [row for row in rows if row["status"] == "STOCKOUT"]


def get_low_stock_report(organization_ids=None, facility_id=None):
    rows = get_medicine_stock_status(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    return [row for row in rows if row["status"] in ["CRITICAL", "LOW"]]


def get_high_coverage_report(
    organization_ids=None,
    facility_id=None,
):
    rows = get_medicine_stock_status(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    return [row for row in rows if row["status"] == "HIGH_COVERAGE"]


def get_expiry_report(
    organization_ids=None,
    facility_id=None,
    days=DEFAULT_NEAR_EXPIRY_DAYS,
):
    if not 1 <= days <= 730:
        raise ValidationError("Expiry reporting days must be between 1 and 730.")

    today = timezone.localdate()
    cutoff = today + timedelta(days=days)

    balances = get_reporting_balances(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    rows = []

    for balance, facility in balances:
        batch = balance.batch

        if not batch.expiry_date:
            continue

        if batch.expiry_date > cutoff:
            continue

        if not facility:
            continue

        if batch.expiry_date < today:
            expiry_status = "EXPIRED"
        elif batch.expiry_date == today:
            expiry_status = "EXPIRES_TODAY"
        else:
            expiry_status = "NEAR_EXPIRY"

        rows.append(
            {
                "facility_id": str(facility.pk),
                "facility_name": facility.name,
                "medicine_id": str(batch.medicine_id),
                "medicine_code": batch.medicine.code,
                "medicine_name": batch.medicine.generic_name,
                "batch_id": str(batch.pk),
                "batch_number": batch.batch_number,
                "expiry_date": batch.expiry_date.isoformat(),
                "days_until_expiry": (batch.expiry_date - today).days,
                "on_hand": str(balance.quantity_on_hand),
                "reserved": str(balance.quantity_reserved),
                "available": str(get_available_quantity(balance)),
                "status": expiry_status,
            }
        )

    return sorted(
        rows,
        key=lambda row: row["expiry_date"],
    )


def get_essential_medicine_availability(
    organization_ids=None,
    facility_id=None,
):
    """
    Report the available stock of medicines marked essential
    in the medicine catalog.

    Adapt the is_essential field if Phase 12 stores this
    information through an EssentialMedicineListItem relation.
    """
    rows = get_medicine_stock_status(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    return [row for row in rows if row["medicine"].get("is_essential", False)]


def get_stock_dashboard_summary(
    organization_ids=None,
    facility_id=None,
):
    rows = get_medicine_stock_status(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    expiry_rows = get_expiry_report(
        organization_ids=organization_ids,
        facility_id=facility_id,
    )

    summary = {
        "facilities_reporting": len({row["facility_id"] for row in rows}),
        "medicine_facility_records": len(rows),
        "stockout_count": 0,
        "critical_stock_count": 0,
        "low_stock_count": 0,
        "adequate_stock_count": 0,
        "high_coverage_count": 0,
        "no_consumption_history_count": 0,
        "expired_batch_count": 0,
        "near_expiry_batch_count": 0,
    }

    for row in rows:
        status = row["status"]

        if status == "STOCKOUT":
            summary["stockout_count"] += 1
        elif status == "CRITICAL":
            summary["critical_stock_count"] += 1
        elif status == "LOW":
            summary["low_stock_count"] += 1
        elif status == "ADEQUATE":
            summary["adequate_stock_count"] += 1
        elif status == "HIGH_COVERAGE":
            summary["high_coverage_count"] += 1
        elif status == "NO_CONSUMPTION_HISTORY":
            summary["no_consumption_history_count"] += 1

    for row in expiry_rows:
        if row["status"] == "EXPIRED":
            summary["expired_batch_count"] += 1
        else:
            summary["near_expiry_batch_count"] += 1

    return summary
