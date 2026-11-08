from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medicines.models import Country
from apps.organizations.models import Organization

from apps.suppliers.models import (
    Supplier,
    SupplierStatus,
    SupplierType,
)


class Command(BaseCommand):
    help = "Seed demonstration supplier records."

    @transaction.atomic
    def handle(self, *args, **options):
        country = Country.objects.filter(code="ET").first()

        if not country:
            self.stdout.write(
                self.style.WARNING(
                    "Ethiopia country record not found. "
                    "Run seed_classification first."
                )
            )
            return

        organization = Organization.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).first()

        suppliers = [
            {
                "code": "SUP-DEMO-001",
                "name": "Demo Pharmaceutical Manufacturer",
                "supplier_type": SupplierType.MANUFACTURER,
                "email": "manufacturer@example.test",
                "phone": "+251900000001",
            },
            {
                "code": "SUP-DEMO-002",
                "name": "Demo Medicine Distributor",
                "supplier_type": SupplierType.DISTRIBUTOR,
                "email": "distributor@example.test",
                "phone": "+251900000002",
            },
            {
                "code": "SUP-DEMO-003",
                "name": "Demo Wholesale Supplier",
                "supplier_type": SupplierType.WHOLESALER,
                "email": "wholesale@example.test",
                "phone": "+251900000003",
            },
        ]

        for item in suppliers:
            Supplier.objects.update_or_create(
                code=item["code"],
                defaults={
                    **item,
                    "country": country,
                    "organization": organization,
                    "status": SupplierStatus.PENDING,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(suppliers)} demonstration suppliers."
            )
        )