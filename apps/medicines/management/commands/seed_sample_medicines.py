from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    Medicine,
    TherapeuticCategory,
)

SAMPLE_MEDICINES = [
    {
        "code": "MED-PAR-500-TAB",
        "generic_name": "Paracetamol",
        "brand_name": "",
        "dosage_form": "TABLET",
        "route": "ORAL",
        "strength_value": "500",
        "strength_unit": "MG",
        "strength_display": "500 mg",
        "dispensing_unit": "TABLET",
        "pack_size": 100,
        "category": "ANALGESICS",
        "atc_code": "N02BE01",
        "is_essential": True,
    },
    {
        "code": "MED-AMX-500-CAP",
        "generic_name": "Amoxicillin",
        "brand_name": "",
        "dosage_form": "CAPSULE",
        "route": "ORAL",
        "strength_value": "500",
        "strength_unit": "MG",
        "strength_display": "500 mg",
        "dispensing_unit": "CAPSULE",
        "pack_size": 100,
        "category": "ANTI_INFECTIVES",
        "atc_code": "J01CA04",
        "is_essential": True,
    },
    {
        "code": "MED-ORS-POWDER",
        "generic_name": "Oral rehydration salts",
        "brand_name": "",
        "dosage_form": "POWDER",
        "route": "ORAL",
        "strength_value": None,
        "strength_unit": None,
        "strength_display": "Standard sachet formulation",
        "dispensing_unit": "PACK",
        "pack_size": 1,
        "category": "GASTROINTESTINAL",
        "atc_code": "",
        "is_essential": True,
    },
    {
        "code": "MED-INS-100",
        "generic_name": "Human insulin",
        "brand_name": "",
        "dosage_form": "INJECTION",
        "route": "SC",
        "strength_value": None,
        "strength_unit": None,
        "strength_display": "100 IU/mL",
        "dispensing_unit": "VIAL",
        "pack_size": 1,
        "category": "ANTIDIABETICS",
        "atc_code": "A10AB01",
        "is_essential": True,
    },
    {
        "code": "MED-SAL-NEB",
        "generic_name": "Salbutamol",
        "brand_name": "",
        "dosage_form": "INHALER",
        "route": "INHALATION",
        "strength_value": None,
        "strength_unit": None,
        "strength_display": "100 micrograms per actuation",
        "dispensing_unit": "PACK",
        "pack_size": 1,
        "category": "RESPIRATORY",
        "atc_code": "R03AC02",
        "is_essential": True,
    },
]


class Command(BaseCommand):
    help = "Seed demonstration medicines."

    @transaction.atomic
    def handle(self, *args, **options):
        count = 0

        for item in SAMPLE_MEDICINES:
            defaults = {
                "generic_name": item["generic_name"],
                "brand_name": item["brand_name"],
                "dosage_form": DosageForm.objects.get(code=item["dosage_form"]),
                "administration_route": AdministrationRoute.objects.get(
                    code=item["route"]
                ),
                "strength_value": item["strength_value"],
                "strength_unit": (
                    MeasurementUnit.objects.get(code=item["strength_unit"])
                    if item["strength_unit"]
                    else None
                ),
                "strength_display": item["strength_display"],
                "dispensing_unit": MeasurementUnit.objects.get(
                    code=item["dispensing_unit"]
                ),
                "pack_size": item["pack_size"],
                "therapeutic_category": TherapeuticCategory.objects.get(
                    code=item["category"]
                ),
                "atc_code": item["atc_code"],
                "is_essential": item["is_essential"],
                "is_active": True,
            }

            Medicine.objects.update_or_create(
                code=item["code"],
                defaults=defaults,
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created or updated {count} sample medicines.")
        )
