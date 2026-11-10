from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class ReplenishmentAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="replenishment.api@example.test",
            username="replenishment_api",
            password="SecurePassword123!",
        )

    def test_request_list_requires_authentication(self):
        response = self.client.get("/api/v1/replenishment/requests/")

        self.assertEqual(response.status_code, 401)

    def test_request_creation_requires_authentication(self):
        response = self.client.post(
            "/api/v1/replenishment/requests/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_policy_request_requires_authentication(self):
        response = self.client.post(
            "/api/v1/replenishment/requests/from-policy/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
