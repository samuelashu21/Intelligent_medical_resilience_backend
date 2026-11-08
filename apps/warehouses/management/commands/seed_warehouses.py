from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Organization

from apps.warehouses.models import (
    StorageLocation,
    StorageType,
    StorageZone,
    Warehouse,
    WarehouseStatus,
    WarehouseType,
)


class Command(BaseCommand):
    help = "Create demonstration warehouse records."

    @transaction.atomic
    def handle(self, *args, **options):
        organization = Organization.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).first()

        if not organization:
            self.stdout.write(
                self.style.ERROR(
                    "No active root organization found. "
                    "Run seed_organizations first."
                )
            )
            return

        warehouse, created = Warehouse.objects.update_or_create(
            code="WH-DEMO-001",
            defaults={
                "name": "Demonstration Central Medical Store",
                "warehouse_type": WarehouseType.CENTRAL,
                "organization": organization,
                "address": "Demonstration warehouse address",
                "city": "Addis Ababa",
                "administrative_area": "Demonstration Area",
                "latitude": 9.0300,
                "longitude": 38.7400,
                "total_capacity": 1000,
                "capacity_unit": "CUBIC_METER",
                "status": WarehouseStatus.ACTIVE,
                "is_cold_chain_capable": True,
                "has_backup_power": True,
                "has_temperature_monitoring": True,
                "phone": "+251900000020",
                "email": "warehouse@example.test",
            },
        )

        ambient_zone, _ = StorageZone.objects.update_or_create(
            warehouse=warehouse,
            code="AMBIENT-01",
            defaults={
                "name": "Ambient Storage Zone",
                "storage_type": StorageType.AMBIENT,
                "capacity": 700,
                "capacity_unit": "CUBIC_METER",
                "minimum_temperature": 15,
                "maximum_temperature": 25,
                "is_active": True,
            },
        )

        cold_zone, _ = StorageZone.objects.update_or_create(
            warehouse=warehouse,
            code="COLD-01",
            defaults={
                "name": "Refrigerated Storage Zone",
                "storage_type": StorageType.REFRIGERATED,
                "capacity": 200,
                "capacity_unit": "CUBIC_METER",
                "minimum_temperature": 2,
                "maximum_temperature": 8,
                "is_active": True,
            },
        )

        StorageLocation.objects.update_or_create(
            zone=ambient_zone,
            code="A1-R1-S1",
            defaults={
                "name": "Ambient shelf 1",
                "aisle": "A1",
                "rack": "R1",
                "shelf": "S1",
                "capacity": 10,
                "capacity_unit": "CUBIC_METER",
                "is_active": True,
            },
        )

        StorageLocation.objects.update_or_create(
            zone=cold_zone,
            code="C1-R1-S1",
            defaults={
                "name": "Cold-chain shelf 1",
                "aisle": "C1",
                "rack": "R1",
                "shelf": "S1",
                "capacity": 5,
                "capacity_unit": "CUBIC_METER",
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Warehouse {'created' if created else 'updated'}: "
                f"{warehouse.code}"
            )
        )