from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationUnitType

from apps.warehouses.models import (
    StorageType,
    StorageZone,
    Warehouse,
    WarehouseStatus,
    WarehouseTemperatureReading,
    WarehouseType,
)

from apps.warehouses.services import (
    activate_warehouse,
    classify_temperature_reading,
    get_warehouse_capacity_summary,
    get_warehouse_temperature_summary,
    set_warehouse_maintenance,
    suspend_warehouse,
)


class WarehouseServiceTests(TestCase):

    def setUp(self):
        # Create a valid OrganizationUnitType to satisfy organization validation rules
        self.org_type = OrganizationUnitType.objects.create(
            code="REGION_TYPE",
            name="Region Level",
            level=1,
        )

        self.organization = Organization.objects.create(
            code="WH-SERVICE-ORG",
            name="Warehouse Service Organization",
            organization_type=self.org_type,
        )

        self.user = User.objects.create_user(
            email="warehouse.service@example.test",
            username="warehouse_service",
            password="SecurePassword123!",
        )

        self.warehouse = Warehouse.objects.create(
            code="WH-SERVICE-001",
            name="Service Test Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
            status=WarehouseStatus.DRAFT,
            total_capacity=1000,
        )

        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="COLD-SERVICE",
            name="Cold Storage",
            storage_type=StorageType.REFRIGERATED,
            minimum_temperature=Decimal("2"),
            maximum_temperature=Decimal("8"),
        )

    def test_activate_warehouse(self):
        warehouse = activate_warehouse(
            warehouse_id=self.warehouse.pk,
        )

        self.assertEqual(
            warehouse.status,
            WarehouseStatus.ACTIVE,
        )

    def test_suspend_warehouse(self):
        activate_warehouse(warehouse_id=self.warehouse.pk)

        warehouse = suspend_warehouse(
            warehouse_id=self.warehouse.pk,
            reason="Safety inspection.",
        )

        self.assertEqual(
            warehouse.status,
            WarehouseStatus.SUSPENDED,
        )

    def test_maintenance_warehouse(self):
        activate_warehouse(warehouse_id=self.warehouse.pk)

        warehouse = set_warehouse_maintenance(
            warehouse_id=self.warehouse.pk,
            reason="Refrigeration repair.",
        )

        self.assertEqual(
            warehouse.status,
            WarehouseStatus.MAINTENANCE,
        )

    def test_cannot_suspend_draft_warehouse(self):
        with self.assertRaises(ValidationError):
            suspend_warehouse(
                warehouse_id=self.warehouse.pk,
                reason="Test",
            )

    def test_temperature_classification(self):
        reading = WarehouseTemperatureReading.objects.create(
            warehouse=self.warehouse,
            zone=self.zone,
            temperature=Decimal("5"),
        )

        result = classify_temperature_reading(reading)

        self.assertEqual(
            result["status"],
            "WITHIN_RANGE",
        )

    def test_temperature_outside_range(self):
        reading = WarehouseTemperatureReading.objects.create(
            warehouse=self.warehouse,
            zone=self.zone,
            temperature=Decimal("12"),
        )

        result = classify_temperature_reading(reading)

        self.assertEqual(
            result["status"],
            "ABOVE_RANGE",
        )

    def test_temperature_summary_without_readings(self):
        summary = get_warehouse_temperature_summary(
            self.warehouse
        )

        self.assertEqual(
            summary["latest_status"],
            "NO_DATA",
        )

    def test_capacity_summary_without_snapshots(self):
        summary = get_warehouse_capacity_summary(
            self.warehouse
        )

        self.assertIsNone(
            summary["utilization_percentage"]
        )