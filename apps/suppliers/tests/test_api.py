from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import (
    AccessPermission,
    Role,
    User,
)
from apps.accounts.services import assign_role
from apps.medicines.models import Country
from apps.organizations.models import Organization, OrganizationUnitType
from apps.suppliers.models import Supplier


class SupplierAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="supplier.api@example.test",
            username="supplier_api",
            password="SecurePassword123!",
        )

        self.role = Role.objects.create(
            code="SUPPLIER_API_TEST_ROLE",
            name="Supplier API Test Role",
        )

        permissions = []

        for code in [
            "suppliers.view",
            "suppliers.create",
            "suppliers.update",
        ]:
            permission, _ = AccessPermission.objects.get_or_create(
                code=code,
                defaults={
                    "name": code.replace(".", " ").title(),
                    "module": "suppliers",
                },
            )

            permissions.append(permission)

        self.role.permissions.add(*permissions)

        assign_role(
            user=self.user,
            role=self.role,
        )

        self.country = Country.objects.create(
            code="ET",
            name="Ethiopia",
        )

        self.org_type, _ = OrganizationUnitType.objects.get_or_create(
            code="MINISTRY",
            defaults={
                "name": "Ministry",
                "level": 1,
            },
        )

        self.organization = Organization.objects.create(
            name="Test Health Organization",
            code="ORG-001",
            organization_type=self.org_type,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {AccessToken.for_user(self.user)}"
            )
        )

    def test_unauthenticated_supplier_list(self):
        self.client.credentials()

        response = self.client.get(
            "/api/v1/suppliers/suppliers/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_create_supplier(self):
        payload = {
            "code": "API-SUP-001",
            "name": "API Test Supplier",
            "supplier_type": "DISTRIBUTOR",
            "country": str(self.country.pk),
            "organization": str(self.organization.pk),
            "email": "api-supplier@example.test",
            "phone": "+251900000010",
            "website": "",
            "address": "Demonstration address",
            "notes": "",
        }

        response = self.client.post(
            "/api/v1/suppliers/suppliers/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        supplier = Supplier.objects.get(code="API-SUP-001")

        self.assertEqual(supplier.status, "PENDING")
        self.assertEqual(supplier.created_by, self.user)

    def test_supplier_cannot_be_deleted(self):
        supplier = Supplier.objects.create(
            code="API-SUP-DELETE",
            name="Protected Supplier",
            supplier_type="DISTRIBUTOR",
            country=self.country,
            organization=self.organization,
        )

        # This test uses a superuser to isolate the deletion rule.
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

        response = self.client.delete(
            f"/api/v1/suppliers/suppliers/{supplier.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            Supplier.objects.filter(pk=supplier.pk).exists()
        )