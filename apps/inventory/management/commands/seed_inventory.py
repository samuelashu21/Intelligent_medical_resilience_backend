from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.medicines.models import Medicine
from apps.warehouses.models import (
    StorageLocation,
    Warehouse,
)

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
)


class Command(BaseCommand):
    help = "Create demonstration stock batches with zero opening balances."

    def add_arguments(self, parser):
        parser.add_argument(
            "--warehouse",
            type=str,
            required=True,
            help="Warehouse UUID or code.",
        )

        parser.add_argument(
            "--medicine",
            type=str,
            required=True,
            help="Medicine UUID or code.",
        )

        parser.add_argument(
            "--location",
            type=str,
            required=True,
            help="Storage location UUID or code.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        warehouse_identifier = options["warehouse"]
        medicine_identifier = options["medicine"]
        location_identifier = options["location"]

        warehouse = (
            Warehouse.objects.filter(pk=warehouse_identifier).first()
            or Warehouse.objects.filter(code=warehouse_identifier).first()
        )

        medicine = (
            Medicine.objects.filter(pk=medicine_identifier).first()
            or Medicine.objects.filter(code=medicine_identifier).first()
        )

        location = (
            StorageLocation.objects.filter(pk=location_identifier).first()
            or StorageLocation.objects.filter(code=location_identifier).first()
        )

        if not warehouse:
            raise CommandError("Warehouse not found.")

        if not medicine:
            raise CommandError("Medicine not found.")

        if not location:
            raise CommandError("Storage location not found.")

        if location.zone.warehouse_id != warehouse.pk:
            raise CommandError(
                "The storage location does not belong to this warehouse."
            )

        today = timezone.localdate()

        batch, created = StockBatch.objects.get_or_create(
            medicine=medicine,
            presentation=None,
            warehouse=warehouse,
            location=location,
            batch_number="DEMO-BATCH-001",
            defaults={
                "manufacture_date": today - timedelta(days=30),
                "expiry_date": today + timedelta(days=365),
                "received_date": today,
                "currency": "USD",
                "notes": "Demonstration batch. No stock received yet.",
            },
        )

        InventoryBalance.objects.get_or_create(
            batch=batch,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch {'created' if created else 'already exists'}: "
                f"{batch.batch_number}. Opening quantity is zero."
            )
        )
