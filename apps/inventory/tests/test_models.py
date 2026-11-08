from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationUnitType
from apps.medicines.models import DosageForm, Medicine
from apps.warehouses.models import (
    StorageLocation,
    StorageType,
    StorageZone,
    Warehouse,
    WarehouseType,
)

from apps.inventory.models import (
    InventoryBalance,
    MovementType,
    StockBatch,
    StockMovement,
)


class InventoryModelTests(TestCase):

    def setUp(self):
        # OrganizationUnitType is a model, so we need to create an instance first
        self.org_type = OrganizationUnitType.objects.create(
            code="HEALTH_FACILITY",
            name="Health Facility",
            level=2,
        )

        self.organization = Organization.objects.create(
            code="INV-TEST-ORG",
            name="Inventory Test Organization",
            organization_type=self.org_type,
        )

        self.user = User.objects.create_user(
            email="inventory.test@example.test",
            username="inventory_test",
            password="SecurePassword123!",
        )

        self.warehouse = Warehouse.objects.create(
            code="INV-WH-001",
            name="Inventory Test Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
        )

        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="INV-ZONE-001",
            name="Ambient Zone",
            storage_type=StorageType.AMBIENT,
        )

        self.location = StorageLocation.objects.create(
            zone=self.zone,
            code="INV-LOC-001",
            name="Shelf 1",
        )

        # DosageForm is a related model, so create an instance for testing
        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        self.medicine = Medicine.objects.create(
            code="INV-MED-001",
            generic_name="Demonstration Medicine",
            dosage_form=self.dosage_form,
        )

        self.batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.location,
            batch_number="BATCH-001",
            manufacture_date=timezone.localdate() - timedelta(days=30),
            expiry_date=timezone.localdate() + timedelta(days=365),
        )

    def test_stock_batch_creation(self):
        self.assertEqual(
            self.batch.batch_number,
            "BATCH-001",
        )

    def test_batch_expiry(self):
        self.assertFalse(self.batch.is_expired)
        self.assertGreater(self.batch.days_until_expiry, 0)

    def test_inventory_balance_creation(self):
        balance = InventoryBalance.objects.create(
            batch=self.batch,
            quantity_on_hand=Decimal("100"),
            quantity_reserved=Decimal("20"),
        )

        self.assertEqual(
            balance.quantity_available,
            Decimal("80"),
        )

    def test_reserved_quantity_cannot_exceed_on_hand(self):
        balance = InventoryBalance(
            batch=self.batch,
            quantity_on_hand=Decimal("10"),
            quantity_reserved=Decimal("20"),
        )

        with self.assertRaises(ValidationError):
            balance.full_clean()

    def test_movement_requires_positive_quantity(self):
        movement = StockMovement(
            batch=self.batch,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal("0"),
            performed_by=self.user,
        )

        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_movement_is_immutable(self):
        movement = StockMovement.objects.create(
            batch=self.batch,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal("10"),
            performed_by=self.user,
        )

        movement.notes = "Attempted modification."

        with self.assertRaises(ValidationError):
            movement.save()

        with self.assertRaises(ValidationError):
            movement.delete()