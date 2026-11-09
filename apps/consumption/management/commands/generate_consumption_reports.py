from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.facilities.models import Facility
from apps.medicines.models import Medicine

from apps.consumption.services import generate_monthly_report


class Command(BaseCommand):
    help = (
        "Generate draft monthly consumption reports "
        "from daily consumption records."
    )

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--month", type=int, required=True)

    def handle(self, *args, **options):
        year = options["year"]
        month = options["month"]

        if not 1 <= month <= 12:
            raise CommandError("Month must be between 1 and 12.")

        if (year, month) > (
            timezone.localdate().year,
            timezone.localdate().month,
        ):
            raise CommandError(
                "Cannot generate reports for a future month."
            )

        created_or_updated = 0

        records = (
            Facility.objects.filter(is_active=True)
            .values_list("id", flat=True)
        )

        for facility_id in records:
            facility = Facility.objects.get(pk=facility_id)

            medicine_ids = (
                facility.daily_consumption_records
                .filter(
                    consumption_date__year=year,
                    consumption_date__month=month,
                )
                .values_list("medicine_id", flat=True)
                .distinct()
            )

            for medicine_id in medicine_ids:
                medicine = Medicine.objects.get(pk=medicine_id)

                try:
                    report = generate_monthly_report(
                        facility=facility,
                        medicine=medicine,
                        year=year,
                        month=month,
                        opening_balance=0,
                        received_quantity=0,
                        losses_quantity=0,
                        closing_balance=0,
                        reporting_unit="UNIT",
                        notes=(
                            "Generated from daily consumption records. "
                            "Review stock balance fields before submission."
                        ),
                    )
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(
                            f"{facility.name} / {medicine.generic_name}: {exc}"
                        )
                    )
                    continue

                created_or_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {created_or_updated} monthly reports."
            )
        )