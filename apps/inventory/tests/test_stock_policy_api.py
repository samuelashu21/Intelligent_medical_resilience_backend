from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class StockPolicyAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="policy.user@example.test",
            username="policy_user",
            password="SecurePassword123!",
        )

    def test_policy_list_requires_authentication(self):
        response = self.client.get(
            "/api/v1/inventory/policies/policies/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_policy_evaluation_requires_authentication(self):
        response = self.client.get(
            "/api/v1/inventory/policies/evaluate/",
        )

        self.assertEqual(
            response.status_code,
            401,
        )