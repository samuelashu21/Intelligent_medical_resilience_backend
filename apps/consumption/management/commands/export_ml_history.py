import csv

from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.consumption.models import MonthlyConsumptionReport


class Command(BaseCommand):

    help = (
        "Export approved monthly consumption reports "
        "for the MediResilience AI ML pipeline."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Destination CSV path.",
        )

        parser.add_argument(
            "--start-year",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--end-year",
            type=int,
            default=None,
        )

    def handle(self, *args, **options):

        output_path = Path(
            options["output"]
        ).resolve()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        queryset = MonthlyConsumptionReport.objects.all()

        if options["start_year"]:
            queryset = queryset.filter(
                year__gte=options["start_year"]
            )

        if options["end_year"]:
            queryset = queryset.filter(
                year__lte=options["end_year"]
            )

        queryset = queryset.order_by(
            "facility_id",
            "medicine_id",
            "year",
            "month",
        )

        fields = [
            "facility_id",
            "medicine_id",
            "year",
            "month",
            "opening_stock",
            "received_quantity",
            "consumed_quantity",
            "losses_quantity",
            "closing_stock",
            "stockout_days",
            "reporting_unit",
            "status",
        ]

        exported = 0

        try:

            with output_path.open(
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as csv_file:

                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=[
                        "facility_id",
                        "medicine_id",
                        "year",
                        "month",
                        "opening_stock",
                        "received_quantity",
                        "consumed_quantity",
                        "losses_quantity",
                        "closing_stock",
                        "stockout_days",
                        "unit_code",
                        "status",
                    ],
                )

                writer.writeheader()

                for report in queryset.iterator(
                    chunk_size=2000
                ):

                    writer.writerow({
                        "facility_id": str(
                            report.facility_id
                        ),
                        "medicine_id": str(
                            report.medicine_id
                        ),
                        "year": report.year,
                        "month": report.month,
                        "opening_stock": (
                            report.opening_stock
                        ),
                        "received_quantity": (
                            report.received_quantity
                        ),
                        "consumed_quantity": (
                            report.consumed_quantity
                        ),
                        "losses_quantity": (
                            report.losses_quantity
                        ),
                        "closing_stock": (
                            report.closing_stock
                        ),
                        "stockout_days": (
                            report.stockout_days
                        ),
                        "unit_code": (
                            report.reporting_unit
                        ),
                        "status": (
                            report.status
                        ),
                    })

                    exported += 1

        except Exception as exc:

            raise CommandError(
                f"Could not export monthly reports: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {exported} monthly reports "
                f"to {output_path}"
            )
        )