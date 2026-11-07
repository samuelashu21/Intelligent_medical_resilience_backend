from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import OrganizationUnitType


ORGANIZATION_TYPES = [
    { 
        "code": "NATIONAL",
        "name": "National",
        "level": 1,
        "parent_code": None,
    },
    {
        "code": "REGION",
        "name": "Region",
        "level": 2,
        "parent_code": "NATIONAL",
    },
    {
        "code": "ZONE",
        "name": "Zone",
        "level": 3,
        "parent_code": "REGION",
    },
    {
        "code": "DISTRICT",
        "name": "District",
        "level": 4,
        "parent_code": "ZONE",
    },
]


class Command(BaseCommand):
    help = "Seed configurable organization hierarchy types."

    @transaction.atomic
    def handle(self, *args, **options):
        for item in ORGANIZATION_TYPES:
            parent = None

            if item["parent_code"]:
                parent = OrganizationUnitType.objects.get(
                    code=item["parent_code"]
                )

            organization_type, created = (
                OrganizationUnitType.objects.update_or_create(
                    code=item["code"],
                    defaults={
                        "name": item["name"],
                        "level": item["level"],
                        "parent_type": parent,
                        "is_active": True,
                    },
                )
            )

            action = "Created" if created else "Updated"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action}: {organization_type.code}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Organization types seeded successfully."
            )
        ) 