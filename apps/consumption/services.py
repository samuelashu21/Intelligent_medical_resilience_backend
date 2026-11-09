from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.consumption.models import (
    ConsumptionAnomaly,
    ConsumptionAnomalyType,
    ConsumptionRecordStatus,
    DailyConsumption,
    MonthlyConsumptionReport,
)


def get_month_date_range(year, month):
    if not 1 <= month <= 12:
        raise ValidationError("Month must be between 1 and 12.")

    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    return start, end


@transaction.atomic
def record_consumption(
    facility,
    medicine,
    consumption_date,
    quantity,
    unit_code,
    recorded_by,
    batch=None,
    source="DISPENSING",
    reference_number="",
    notes="",
):
    quantity = Decimal(str(quantity))

    if quantity < 0:
        raise ValidationError(
            "Consumption quantity cannot be negative."
        )

    if consumption_date > timezone.localdate():
        raise ValidationError(
            "Future-dated consumption cannot be recorded."
        )

    if batch:
        if batch.medicine_id != medicine.pk:
            raise ValidationError(
                "The batch does not belong to the selected medicine."
            )

        if batch.warehouse.organization_id != facility.organization_id:
            raise ValidationError(
                "The batch does not belong to the facility organization."
            )

    record = DailyConsumption.objects.create(
        facility=facility,
        medicine=medicine,
        batch=batch,
        consumption_date=consumption_date,
        quantity=quantity,
        unit_code=unit_code,
        recorded_by=recorded_by,
        source=source,
        reference_number=reference_number,
        notes=notes,
    )

    return record


def calculate_monthly_consumption(
    facility_id,
    medicine_id,
    year,
    month,
):
    start_date, end_date = get_month_date_range(year, month)

    result = DailyConsumption.objects.filter(
        facility_id=facility_id,
        medicine_id=medicine_id,
        consumption_date__gte=start_date,
        consumption_date__lte=end_date,
    ).aggregate(
        total=Sum("quantity")
    )

    return result["total"] or Decimal("0")


def calculate_average_monthly_consumption(
    facility_id,
    medicine_id,
    number_of_months=3,
    as_of=None,
):
    if number_of_months < 1:
        raise ValidationError(
            "The number of months must be at least one."
        )

    as_of = as_of or timezone.localdate()

    total = Decimal("0")
    complete_months = 0

    # Use completed calendar months only. This prevents an incomplete
    # current month from artificially reducing the average.
    year = as_of.year
    month = as_of.month - 1

    if month == 0:
        month = 12
        year -= 1

    for _ in range(number_of_months):
        result = calculate_monthly_consumption(
            facility_id=facility_id,
            medicine_id=medicine_id,
            year=year,
            month=month,
        )

        total += result
        complete_months += 1

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    return {
        "average_monthly_consumption": (
            total / Decimal(complete_months)
        ),
        "months_included": complete_months,
        "total_consumption": total,
    }


@transaction.atomic
def generate_monthly_report(
    facility,
    medicine,
    year,
    month,
    opening_balance,
    received_quantity,
    losses_quantity,
    closing_balance,
    reporting_unit,
    stockout_days=0,
    notes="",
):
    start_date, end_date = get_month_date_range(year, month)

    consumed_quantity = calculate_monthly_consumption(
        facility_id=facility.pk,
        medicine_id=medicine.pk,
        year=year,
        month=month,
    )

    report, created = MonthlyConsumptionReport.objects.get_or_create(
        facility=facility,
        medicine=medicine,
        year=year,
        month=month,
        defaults={
            "opening_balance": opening_balance,
            "received_quantity": received_quantity,
            "consumed_quantity": consumed_quantity,
            "losses_quantity": losses_quantity,
            "closing_balance": closing_balance,
            "reporting_unit": reporting_unit,
            "stockout_days": stockout_days,
            "notes": notes,
        },
    )

    if not created:
        if report.status != ConsumptionRecordStatus.DRAFT:
            raise ValidationError(
                "Only draft reports can be regenerated."
            )

        report.opening_balance = opening_balance
        report.received_quantity = received_quantity
        report.consumed_quantity = consumed_quantity
        report.losses_quantity = losses_quantity
        report.closing_balance = closing_balance
        report.reporting_unit = reporting_unit
        report.stockout_days = stockout_days
        report.notes = notes
        report.save()

    return report


@transaction.atomic
def submit_monthly_report(report_id, submitted_by):
    report = MonthlyConsumptionReport.objects.select_for_update().get(
        pk=report_id
    )

    if report.status != ConsumptionRecordStatus.DRAFT:
        raise ValidationError(
            "Only draft reports can be submitted."
        )

    report.status = ConsumptionRecordStatus.SUBMITTED
    report.submitted_by = submitted_by
    report.submitted_at = timezone.now()
    report.save()

    return report


@transaction.atomic
def approve_monthly_report(report_id, approved_by):
    report = MonthlyConsumptionReport.objects.select_for_update().get(
        pk=report_id
    )

    if report.status != ConsumptionRecordStatus.SUBMITTED:
        raise ValidationError(
            "Only submitted reports can be approved."
        )

    if report.submitted_by_id == approved_by.pk:
        raise ValidationError(
            "The submitter cannot approve their own report."
        )

    report.status = ConsumptionRecordStatus.APPROVED
    report.approved_by = approved_by
    report.approved_at = timezone.now()
    report.rejection_reason = ""
    report.save()

    return report


@transaction.atomic
def reject_monthly_report(report_id, rejected_by, reason):
    if not reason or not reason.strip():
        raise ValidationError(
            "A rejection reason is required."
        )

    report = MonthlyConsumptionReport.objects.select_for_update().get(
        pk=report_id
    )

    if report.status != ConsumptionRecordStatus.SUBMITTED:
        raise ValidationError(
            "Only submitted reports can be rejected."
        )

    if report.submitted_by_id == rejected_by.pk:
        raise ValidationError(
            "The submitter cannot reject their own report."
        )

    report.status = ConsumptionRecordStatus.REJECTED
    report.rejection_reason = reason.strip()
    report.save()

    return report


def detect_consumption_anomalies(
    facility,
    medicine,
    year,
    month,
    historical_months=3,
    high_threshold=Decimal("2.0"),
    low_threshold=Decimal("0.5"),
):
    start_date, end_date = get_month_date_range(year, month)

    observed = calculate_monthly_consumption(
        facility.pk,
        medicine.pk,
        year,
        month,
    )

    historical = calculate_average_monthly_consumption(
        facility.pk,
        medicine.pk,
        number_of_months=historical_months,
        as_of=start_date,
    )

    expected = historical["average_monthly_consumption"]

    anomalies = []

    if expected > 0:
        ratio = observed / expected

        if ratio >= high_threshold:
            anomalies.append(
                ConsumptionAnomaly.objects.create(
                    facility=facility,
                    medicine=medicine,
                    anomaly_type=ConsumptionAnomalyType.HIGH_CONSUMPTION,
                    reporting_period_start=start_date,
                    reporting_period_end=end_date,
                    observed_quantity=observed,
                    expected_quantity=expected,
                    description=(
                        "Consumption is substantially higher than "
                        "the historical monthly average."
                    ),
                )
            )

        elif ratio <= low_threshold:
            anomalies.append(
                ConsumptionAnomaly.objects.create(
                    facility=facility,
                    medicine=medicine,
                    anomaly_type=ConsumptionAnomalyType.LOW_CONSUMPTION,
                    reporting_period_start=start_date,
                    reporting_period_end=end_date,
                    observed_quantity=observed,
                    expected_quantity=expected,
                    description=(
                        "Consumption is substantially lower than "
                        "the historical monthly average. Check for "
                        "stockouts or missing reports."
                    ),
                )
            )

    elif observed == 0:
        anomalies.append(
            ConsumptionAnomaly.objects.create(
                facility=facility,
                medicine=medicine,
                anomaly_type=ConsumptionAnomalyType.ZERO_CONSUMPTION,
                reporting_period_start=start_date,
                reporting_period_end=end_date,
                observed_quantity=observed,
                expected_quantity=expected,
                description=(
                    "No consumption was reported. Verify whether "
                    "this reflects zero use, stockout, or missing data."
                ),
            )
        )

    return anomalies