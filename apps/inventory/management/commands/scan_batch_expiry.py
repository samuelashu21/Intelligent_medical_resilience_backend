from django.core.management.base import BaseCommand, CommandError

from apps.inventory.batch_services import scan_batch_expiry


class Command(BaseCommand):
    help = "Scan medicine batches for expiry and near-expiry alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--thresholds",
            nargs="+",
            type=int,
            default=[30, 60, 90],
            help="Expiry warning thresholds in days.",
        )

    def handle(self, *args, **options):
        thresholds = options["thresholds"]

        if any(value < 0 or value > 3650 for value in thresholds):
            raise CommandError("Thresholds must be between 0 and 3650 days.")

        if len(set(thresholds)) != len(thresholds):
            raise CommandError("Thresholds must not contain duplicates.")

        thresholds = tuple(sorted(thresholds))

        result = scan_batch_expiry(thresholds=thresholds)

        self.stdout.write(self.style.SUCCESS("Batch expiry scan completed."))

        for key, value in result.items():
            self.stdout.write(f"{key}: {value}")
