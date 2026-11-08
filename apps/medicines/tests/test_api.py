from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import (
    AccessPermission,
    Role,
    User,
)
from apps.accounts.services import assign_role
from apps.medicines.models import (
    DosageForm,
    Medicine,
)


class MedicineAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="medicine.admin@example.com",
            username="medicine_admin",
            password="SecurePassword123!",
        )

        self.role = Role.objects.create(
            code="MEDICINE_TEST_ROLE",
            name="Medicine Test Role",
        )

        self.permissions = {}

        for code, name in [
            ("medicines.view", "View Medicines"),
            ("medicines.create", "Create Medicines"),
            ("medicines.update", "Update Medicines"),
        ]:
            self.permissions[code] = AccessPermission.objects.create(
                code=code,
                name=name,
                module="medicines",
            )

        self.role.permissions.add(*self.permissions.values())

        assign_role(
            user=self.user,
            role=self.role,
        )

        self.tablet = DosageForm.objects.create(
            code="API_TABLET",
            name="API Tablet",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {AccessToken.for_user(self.user)}"
            )
        )

    def test_list_medicines(self):
        Medicine.objects.create(
            code="API-PAR",
            generic_name="Paracetamol",
            dosage_form=self.tablet,
        )

        response = self.client.get(
            "/api/v1/medicines/catalog/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_create_medicine(self):
        payload = {
            "code": "API-AMX-500",
            "generic_name": "Amoxicillin",
            "dosage_form": str(self.tablet.pk),
            "is_essential": True,
        }

        response = self.client.post(
            "/api/v1/medicines/catalog/",
            payload,
            format="json",
        )

        if response.status_code != status.HTTP_201_CREATED:
            print("\n--- SERIALIZER ERROR RESPONSE ---")
            print(response.data)
            print("---------------------------------\n")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Medicine.objects.filter(
                code="API-AMX-500"
            ).exists()
        )

    def test_unauthenticated_user_cannot_list_medicines(self):
        self.client.credentials()

        response = self.client.get(
            "/api/v1/medicines/catalog/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        ) 