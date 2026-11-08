from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medicines.models import Country


COUNTRIES = [
    ("ET", "Ethiopia"),
    ("KE", "Kenya"),
    ("UG", "Uganda"),
    ("TZ", "Tanzania"),
    ("RW", "Rwanda"),
    ("GH", "Ghana"),
    ("NG", "Nigeria"),
    ("ZA", "South Africa"),
]


class Command(BaseCommand):
    help = "Seed country reference records."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name in COUNTRIES:
            Country.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(COUNTRIES)} country records."
            )
        )