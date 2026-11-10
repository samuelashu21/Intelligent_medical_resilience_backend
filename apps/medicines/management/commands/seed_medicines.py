from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    TherapeuticCategory,
)

DOSAGE_FORMS = [
    ("TABLET", "Tablet"),
    ("CAPSULE", "Capsule"),
    ("ORAL_SOLUTION", "Oral solution"),
    ("SYRUP", "Syrup"),
    ("SUSPENSION", "Oral suspension"),
    ("INJECTION", "Injection"),
    ("INFUSION", "Infusion"),
    ("CREAM", "Cream"),
    ("OINTMENT", "Ointment"),
    ("EYE_DROPS", "Eye drops"),
    ("EAR_DROPS", "Ear drops"),
    ("INHALER", "Inhaler"),
    ("SUPPOSITORY", "Suppository"),
    ("POWDER", "Powder"),
    ("OTHER", "Other"),
]


ROUTES = [
    ("ORAL", "Oral"),
    ("IV", "Intravenous"),
    ("IM", "Intramuscular"),
    ("SC", "Subcutaneous"),
    ("TOPICAL", "Topical"),
    ("INHALATION", "Inhalation"),
    ("OPHTHALMIC", "Ophthalmic"),
    ("OTIC", "Otic"),
    ("RECTAL", "Rectal"),
    ("OTHER", "Other"),
]


UNITS = [
    ("MG", "Milligram", "mg", "MASS"),
    ("G", "Gram", "g", "MASS"),
    ("MCG", "Microgram", "mcg", "MASS"),
    ("ML", "Milliliter", "mL", "VOLUME"),
    ("L", "Liter", "L", "VOLUME"),
    ("UNIT", "Unit", "unit", "COUNT"),
    ("TABLET", "Tablet", "tablet", "COUNT"),
    ("CAPSULE", "Capsule", "capsule", "COUNT"),
    ("VIAL", "Vial", "vial", "COUNT"),
    ("AMPOULE", "Ampoule", "ampoule", "COUNT"),
    ("BOTTLE", "Bottle", "bottle", "COUNT"),
    ("PACK", "Pack", "pack", "COUNT"),
]


CATEGORIES = [
    (
        "ANTI_INFECTIVES",
        "Anti-infectives",
        "Medicines used to prevent or treat infections.",
    ),
    (
        "CARDIOVASCULAR",
        "Cardiovascular medicines",
        "Medicines used in cardiovascular conditions.",
    ),
    (
        "ANALGESICS",
        "Analgesics",
        "Medicines used for pain management.",
    ),
    (
        "ANTIDIABETICS",
        "Antidiabetic medicines",
        "Medicines used in diabetes management.",
    ),
    (
        "RESPIRATORY",
        "Respiratory medicines",
        "Medicines used in respiratory conditions.",
    ),
    (
        "GASTROINTESTINAL",
        "Gastrointestinal medicines",
        "Medicines used in gastrointestinal conditions.",
    ),
]


class Command(BaseCommand):
    help = "Seed medicine catalog reference data."

    @transaction.atomic
    def handle(self, *args, **options):

        for code, name in DOSAGE_FORMS:
            DosageForm.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_active": True,
                },
            )

        for code, name in ROUTES:
            AdministrationRoute.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_active": True,
                },
            )

        for code, name, symbol, unit_type in UNITS:
            MeasurementUnit.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "symbol": symbol,
                    "unit_type": unit_type,
                    "is_active": True,
                },
            )

        for code, name, description in CATEGORIES:
            TherapeuticCategory.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Medicine reference data seeded successfully.")
        )
