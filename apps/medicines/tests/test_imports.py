import csv
import tempfile

from pathlib import Path

from django.test import TestCase

from apps.medicines.models import (
    DosageForm,
    Medicine,
    MedicineImportBatch,
    MedicineImportRow,
)

from apps.medicines.import_services import import_medicine_file


class MedicineImportTests(TestCase):

    def setUp(self):
        DosageForm.objects.create(
            code="IMPORT_TABLET",
            name="Import Tablet",
        )

    def create_csv(self, rows):
        temporary = tempfile.NamedTemporaryFile(
            suffix=".csv",
            delete=False,
            mode="w",
            newline="",
            encoding="utf-8",
        )

        fieldnames = [
            "code",
            "generic_name",
            "dosage_form_code",
            "route_code",
            "strength_display",
            "is_essential",
        ]

        writer = csv.DictWriter(
            temporary,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

        temporary.close()

        return Path(temporary.name)

    def test_successful_import(self):
        file_path = self.create_csv([
            {
                "code": "IMPORT-PAR",
                "generic_name": "Paracetamol",
                "dosage_form_code": "IMPORT_TABLET",
                "route_code": "",
                "strength_display": "500 mg",
                "is_essential": "true",
            }
        ])

        try:
            batch = import_medicine_file(file_path)

            self.assertEqual(batch.status, "COMPLETED")
            self.assertEqual(batch.successful_rows, 1)
            self.assertEqual(batch.failed_rows, 0)

            self.assertTrue(
                Medicine.objects.filter(
                    code="IMPORT-PAR"
                ).exists()
            )

        finally:
            file_path.unlink(missing_ok=True)

    def test_invalid_row_is_recorded(self):
        file_path = self.create_csv([
            {
                "code": "IMPORT-INVALID",
                "generic_name": "Invalid Medicine",
                "dosage_form_code": "UNKNOWN_FORM",
                "route_code": "",
                "strength_display": "",
                "is_essential": "true",
            }
        ])

        try:
            batch = import_medicine_file(file_path)

            self.assertEqual(
                batch.status,
                "COMPLETED_WITH_ERRORS",
            )

            self.assertEqual(batch.failed_rows, 1)

            self.assertTrue(
                MedicineImportRow.objects.filter(
                    batch=batch,
                    status="FAILED",
                ).exists()
            )

        finally:
            file_path.unlink(missing_ok=True)

    def test_reimport_updates_existing_medicine(self):
        rows = [
            {
                "code": "IMPORT-UPDATE",
                "generic_name": "Original Name",
                "dosage_form_code": "IMPORT_TABLET",
                "route_code": "",
                "strength_display": "500 mg",
                "is_essential": "true",
            }
        ]

        file_path = self.create_csv(rows)

        try:
            first = import_medicine_file(file_path)

            self.assertEqual(first.successful_rows, 1)

            rows[0]["generic_name"] = "Updated Name"

            file_path.unlink()

            file_path = self.create_csv(rows)

            second = import_medicine_file(file_path)

            medicine = Medicine.objects.get(
                code="IMPORT-UPDATE"
            )

            self.assertEqual(
                medicine.generic_name,
                "Updated Name",
            )

            self.assertEqual(
                second.successful_rows,
                1,
            )

            self.assertEqual(
                second.rows.first().status,
                "UPDATED",
            )

        finally:
            file_path.unlink(missing_ok=True)