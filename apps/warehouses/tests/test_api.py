from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import (
    AccessPermission,
    Role,
    User,
)

from apps.accounts.services import assign_role

from apps.organizations.models import Organization, OrganizationUnitType

from apps.warehouses.models import Warehouse


class WarehouseAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="warehouse.api@example.test",
            username="warehouse_api",
            password="SecurePassword123!",
        )

        self.org_type = OrganizationUnitType.objects.create(
            code="REGION_TYPE",
            name="Region Level",
            level=1,
        )

        self.organization = Organization.objects.create(
            code="WH-API-ORG",
            name="Warehouse API Organization",
            organization_type=self.org_type,
        )

        self.role = Role.objects.create(
            code="WAREHOUSE_API_TEST",
            name="Warehouse API Test",
        )

        permissions = []

        for code in [
            "warehouses.view",
            "warehouses.create",
            "warehouses.update",
        ]:
            permission, _ = AccessPermission.objects.get_or_create(
                code=code,
                defaults={
                    "name": code.replace(".", " ").title(),
                    "module": "warehouses",
                },
            )
            permissions.append(permission)

        self.role.permissions.add(*permissions)

        assign_role(
            user=self.user,
            role=self.role,
            organization=self.organization,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {AccessToken.for_user(self.user)}"
            )
        )

    def test_unauthenticated_request(self):
        self.client.credentials()

        response = self.client.get(
            "/api/v1/warehouses/warehouses/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_create_warehouse(self):
        payload = {
            "code": "WH-API-001",
            "name": "API Test Warehouse",
            "warehouse_type": "DISTRICT",
            "organization": str(self.organization.pk),
            "address": "Test address",
            "city": "Test city",
            "total_capacity": "500.00",
            "capacity_unit": "CUBIC_METER",
            "is_cold_chain_capable": False,
            "has_backup_power": False,
            "has_temperature_monitoring": False,
        }

        response = self.client.post(
            "/api/v1/warehouses/warehouses/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        warehouse = Warehouse.objects.get(code="WH-API-001")

        self.assertEqual(warehouse.status, "DRAFT")
        self.assertEqual(warehouse.created_by, self.user)

    def test_warehouse_deletion_is_blocked(self):
        warehouse = Warehouse.objects.create(
            code="WH-API-DELETE",
            name="Protected Warehouse",
            warehouse_type="DISTRICT",
            organization=self.organization,
        )

        response = self.client.delete(
            f"/api/v1/warehouses/warehouses/{warehouse.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            Warehouse.objects.filter(pk=warehouse.pk).exists()
        )