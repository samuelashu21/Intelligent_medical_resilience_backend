from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationUnitType

from apps.warehouses.models import (
    StorageLocation,
    StorageType,
    StorageZone,
    Warehouse,
    WarehouseCapacitySnapshot,
    WarehouseManagerAssignment,
    WarehouseTemperatureReading,
    WarehouseType,
)


class WarehouseModelTests(TestCase):

    def setUp(self):
        # Create a valid OrganizationUnitType first to satisfy clean validation rules
        self.org_type = OrganizationUnitType.objects.create(
            code="REGION_TYPE",
            name="Region Level",
            level=1,
        )

        self.organization = Organization.objects.create(
            code="WH-TEST-ORG",
            name="Warehouse Test Organization",
            organization_type=self.org_type,
        )

        self.user = User.objects.create_user(
            email="warehouse.manager@example.test",
            username="warehouse_manager",
            password="SecurePassword123!",
        )

        self.warehouse = Warehouse.objects.create(
            code="WH-TEST-001",
            name="Test Central Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
            total_capacity=Decimal("1000"),
        )

        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="AMBIENT-TEST",
            name="Test Ambient Zone",
            storage_type=StorageType.AMBIENT,
            capacity=Decimal("500"),
            minimum_temperature=Decimal("15"),
            maximum_temperature=Decimal("25"),
        )

    def test_warehouse_creation(self):
        self.assertEqual(
            self.warehouse.warehouse_type,
            WarehouseType.CENTRAL,
        )

    def test_warehouse_code_normalization(self):
        warehouse = Warehouse(
            code=" wh-test-002 ",
            name="Another Warehouse",
            warehouse_type=WarehouseType.REGIONAL,
            organization=self.organization,
        )

        warehouse.save()

        self.assertEqual(warehouse.code, "WH-TEST-002")

    def test_zone_creation(self):
        self.assertEqual(
            self.zone.warehouse,
            self.warehouse,
        )

    def test_invalid_temperature_range(self):
        zone = StorageZone(
            warehouse=self.warehouse,
            code="INVALID",
            name="Invalid Zone",
            storage_type=StorageType.AMBIENT,
            minimum_temperature=Decimal("30"),
            maximum_temperature=Decimal("20"),
        )

        with self.assertRaises(ValidationError):
            zone.full_clean()

    def test_location_creation(self):
        location = StorageLocation.objects.create(
            zone=self.zone,
            code="A1-R1-S1",
            name="Shelf 1",
            aisle="A1",
            rack="R1",
            shelf="S1",
        )

        self.assertEqual(location.zone, self.zone)

    def test_manager_assignment(self):
        assignment = WarehouseManagerAssignment.objects.create(
            warehouse=self.warehouse,
            user=self.user,
            assigned_by=self.user,
        )

        self.assertTrue(assignment.is_active)

    def test_temperature_reading(self):
        reading = WarehouseTemperatureReading.objects.create(
            warehouse=self.warehouse,
            zone=self.zone,
            temperature=Decimal("22.00"),
            humidity=Decimal("50.00"),
            recorded_by=self.user,
        )

        self.assertEqual(reading.temperature, Decimal("22.00"))

    def test_temperature_zone_must_belong_to_warehouse(self):
        other_warehouse = Warehouse.objects.create(
            code="WH-TEST-OTHER",
            name="Other Warehouse",
            warehouse_type=WarehouseType.DISTRICT,
            organization=self.organization,
        )

        reading = WarehouseTemperatureReading(
            warehouse=other_warehouse,
            zone=self.zone,
            temperature=Decimal("22"),
        )

        with self.assertRaises(ValidationError):
            reading.full_clean()

    def test_capacity_snapshot(self):
        snapshot = WarehouseCapacitySnapshot.objects.create(
            warehouse=self.warehouse,
            used_capacity=Decimal("400"),
            available_capacity=Decimal("600"),
            recorded_by=self.user,
        )

        self.assertEqual(
            snapshot.used_capacity,
            Decimal("400"),
        )

    def test_capacity_cannot_exceed_warehouse_total(self):
        snapshot = WarehouseCapacitySnapshot(
            warehouse=self.warehouse,
            used_capacity=Decimal("800"),
            available_capacity=Decimal("500"),
        )

        with self.assertRaises(ValidationError):
            snapshot.full_clean()

    def test_cold_chain_requires_monitoring(self):
        warehouse = Warehouse(
            code="WH-COLD-INVALID",
            name="Cold Warehouse",
            warehouse_type=WarehouseType.COLD_CHAIN,
            organization=self.organization,
            is_cold_chain_capable=True,
            has_temperature_monitoring=False,
        )

        with self.assertRaises(ValidationError):
            warehouse.full_clean()