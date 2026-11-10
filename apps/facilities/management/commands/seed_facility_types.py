from django.core.management.base import BaseCommand
from django.db import transaction

from apps.facilities.models import FacilityType

FACILITY_TYPES = [
    ("HOSPITAL", "Hospital"),
    ("HEALTH_CENTER", "Health Center"),
    ("CLINIC", "Clinic"),
    ("HEALTH_POST", "Health Post"),
    ("PHARMACY", "Pharmacy"),
    ("MEDICAL_STORE", "Medical Store"),
    ("OTHER", "Other Healthcare Facility"),
]


class Command(BaseCommand):
    help = "Seed healthcare facility types."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name in FACILITY_TYPES:
            facility_type, created = FacilityType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_active": True,
                },
            )

            action = "Created" if created else "Updated"

            self.stdout.write(self.style.SUCCESS(f"{action}: {facility_type.name}"))

        self.stdout.write(self.style.SUCCESS("Facility types seeded successfully."))
