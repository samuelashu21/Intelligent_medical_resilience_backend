from datetime import timedelta

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from django.utils import timezone

from apps.accounts.models import (
    AccessPermission,
    Role,
    User,
)

from apps.accounts.services import assign_role

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
    StockBatch,
)


class InventoryAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="inventory.api@example.test",
            username="inventory_api",
            password="SecurePassword123!",
        )

        # 1. Create OrganizationUnitType and Organization
        self.org_type = OrganizationUnitType.objects.create(
            code="HEALTH_FACILITY",
            name="Health Facility",
            level=2,
        )

        self.organization = Organization.objects.create(
            code="INV-API-ORG",
            name="Inventory API Organization",
            organization_type=self.org_type,
        )

        self.role = Role.objects.create(
            code="INVENTORY_API_TEST",
            name="Inventory API Test",
        )

        permission_codes = [
            "inventory.view",
            "inventory.receive",
            "inventory.issue",
            "inventory.adjust",
        ]

        permissions = []

        for code in permission_codes:
            permission, _ = AccessPermission.objects.get_or_create(
                code=code,
                defaults={
                    "name": code.replace(".", " ").title(),
                    "module": "inventory",
                },
            )

            permissions.append(permission)

        self.role.permissions.add(*permissions)

        assign_role(
            user=self.user,
            role=self.role,
            organization=self.organization,
        )

        self.warehouse = Warehouse.objects.create(
            code="INV-API-WH",
            name="Inventory API Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
        )

        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="INV-API-ZONE",
            name="Ambient",
            storage_type=StorageType.AMBIENT,
        )

        self.location = StorageLocation.objects.create(
            zone=self.zone,
            code="INV-API-LOC",
            name="Shelf",
        )

        # 2. Create DosageForm and Medicine
        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        self.medicine = Medicine.objects.create(
            code="INV-API-MED",
            generic_name="Inventory API Medicine",
            dosage_form=self.dosage_form,
        )

        self.batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.location,
            batch_number="INV-API-BATCH",
            expiry_date=timezone.localdate() + timedelta(days=365),
        )

        InventoryBalance.objects.create(batch=self.batch)

        self.client.credentials(
            HTTP_AUTHORIZATION=(f"Bearer {AccessToken.for_user(self.user)}")
        )

    def test_list_stock_batches(self):
        response = self.client.get("/api/v1/inventory/batches/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_receive_stock(self):
        response = self.client.post(
            f"/api/v1/inventory/batches/{self.batch.pk}/receive/",
            {
                "quantity": "100",
                "reference_number": "GRN-API-001",
                "notes": "Demonstration goods receipt.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.batch.balance.refresh_from_db()

        self.assertEqual(
            str(self.batch.balance.quantity_on_hand),
            "100.000",
        )

    def test_stock_balance_endpoint(self):
        response = self.client.get("/api/v1/inventory/balances/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_movement_ledger_is_read_only(self):
        response = self.client.post(
            "/api/v1/inventory/movements/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_unauthenticated_access_is_rejected(self):
        self.client.credentials()

        response = self.client.get("/api/v1/inventory/batches/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
