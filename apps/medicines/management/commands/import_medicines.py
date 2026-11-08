from django.core.management.base import BaseCommand, CommandError

from apps.medicines.import_services import import_medicine_file


class Command(BaseCommand):
    help = "Import medicines from CSV or XLSX files."

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to the medicine CSV or XLSX file.",
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]

        try:
            batch = import_medicine_file(file_path)

        except Exception as exc:
            raise CommandError(
                f"Medicine import failed: {exc}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Import batch: {batch.id}"
            )
        )

        self.stdout.write(
            f"Filename: {batch.filename}"
        )

        self.stdout.write(
            f"Status: {batch.status}"
        )

        self.stdout.write(
            f"Total rows: {batch.total_rows}"
        )

        self.stdout.write(
            f"Successful: {batch.successful_rows}"
        )

        self.stdout.write(
            f"Failed: {batch.failed_rows}"
        )