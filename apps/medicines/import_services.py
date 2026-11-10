import csv
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    Medicine,
    MedicineImportBatch,
    MedicineImportRow,
    TherapeuticCategory,
)


def normalize_boolean(value, default=False):
    if value is None or str(value).strip() == "":
        return default

    normalized = str(value).strip().lower()

    if normalized in ["true", "1", "yes", "y"]:
        return True

    if normalized in ["false", "0", "no", "n"]:
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def normalize_optional_integer(value):
    if value is None or str(value).strip() == "":
        return None

    result = int(value)

    if result <= 0:
        raise ValueError("Value must be greater than zero.")

    return result


def load_import_rows(file_path):
    """
    Read CSV or Excel data into dictionaries.
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".csv":
        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            return list(csv.DictReader(file))

    if extension == ".xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(
            file_path,
            read_only=True,
            data_only=True,
        )

        worksheet = workbook.active

        rows = worksheet.iter_rows(values_only=True)

        headers = next(rows, None)

        if not headers:
            return []

        headers = [str(value).strip() if value is not None else "" for value in headers]

        data = []

        for values in rows:
            data.append(
                {header: value for header, value in zip(headers, values) if header}
            )

        workbook.close()

        return data

    raise ValueError("Only CSV and XLSX files are supported.")


def process_medicine_row(row):
    """
    Validate and create/update one medicine.

    Medicine code is the import matching key.
    """

    code = str(row.get("code") or "").strip().upper()

    generic_name = str(row.get("generic_name") or "").strip()

    dosage_form_code = str(row.get("dosage_form_code") or "").strip().upper()

    if not code:
        raise ValueError("Medicine code is required.")

    if not generic_name:
        raise ValueError("Generic name is required.")

    if not dosage_form_code:
        raise ValueError("Dosage form code is required.")

    dosage_form = DosageForm.objects.filter(
        code=dosage_form_code,
        is_active=True,
    ).first()

    if not dosage_form:
        raise ValueError(f"Unknown dosage form code: {dosage_form_code}")

    route_code = str(row.get("route_code") or "").strip().upper()

    route = None

    if route_code:
        route = AdministrationRoute.objects.filter(
            code=route_code,
            is_active=True,
        ).first()

        if not route:
            raise ValueError(f"Unknown administration route: {route_code}")

    category_code = str(row.get("category_code") or "").strip().upper()

    category = None

    if category_code:
        category = TherapeuticCategory.objects.filter(
            code=category_code,
            is_active=True,
        ).first()

        if not category:
            raise ValueError(f"Unknown therapeutic category: {category_code}")

    pack_size = normalize_optional_integer(row.get("pack_size"))

    defaults = {
        "generic_name": generic_name,
        "brand_name": str(row.get("brand_name") or "").strip(),
        "dosage_form": dosage_form,
        "administration_route": route,
        "therapeutic_category": category,
        "strength_display": str(row.get("strength_display") or "").strip(),
        "atc_code": str(row.get("atc_code") or "").strip().upper(),
        "is_essential": normalize_boolean(
            row.get("is_essential"),
            False,
        ),
        "is_controlled": normalize_boolean(
            row.get("is_controlled"),
            False,
        ),
        "pack_size": pack_size,
    }

    medicine = Medicine.objects.filter(code=code).first()

    created = medicine is None

    if created:
        medicine = Medicine(
            code=code,
            **defaults,
        )
    else:
        for field, value in defaults.items():
            setattr(medicine, field, value)

    medicine.full_clean()
    medicine.save()

    return medicine, created


def import_medicine_file(file_path, uploaded_by=None):
    """
    Import medicine records with per-row validation and results.

    Each row is processed independently so that one invalid row
    does not discard valid rows from the same import.
    """

    file_path = Path(file_path)

    batch = MedicineImportBatch.objects.create(
        uploaded_by=uploaded_by,
        filename=file_path.name,
        status="PROCESSING",
        started_at=timezone.now(),
    )

    try:
        rows = load_import_rows(file_path)
        batch.total_rows = len(rows)
        batch.save(update_fields=["total_rows"])

        for row_number, row in enumerate(rows, start=2):
            code = str(row.get("code") or "").strip().upper()

            try:
                with transaction.atomic():
                    medicine, created = process_medicine_row(row)

                    status = "CREATED" if created else "UPDATED"

                    MedicineImportRow.objects.create(
                        batch=batch,
                        row_number=row_number,
                        medicine_code=medicine.code,
                        status=status,
                        message="Import successful.",
                        source_data=row,
                    )

                    batch.successful_rows += 1

            except Exception as exc:
                MedicineImportRow.objects.create(
                    batch=batch,
                    row_number=row_number,
                    medicine_code=code,
                    status="FAILED",
                    message=str(exc),
                    source_data=row,
                )

                batch.failed_rows += 1

        if batch.failed_rows == 0:
            batch.status = "COMPLETED"
        else:
            batch.status = "COMPLETED_WITH_ERRORS"

        batch.summary = {
            "total": batch.total_rows,
            "successful": batch.successful_rows,
            "failed": batch.failed_rows,
        }

        batch.completed_at = timezone.now()

        batch.save()

    except Exception as exc:
        batch.status = "FAILED"
        batch.summary = {"error": str(exc)}
        batch.completed_at = timezone.now()
        batch.save()

        raise

    return batch
