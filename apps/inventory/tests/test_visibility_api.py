from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class StockVisibilityAPITests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            email="visibility.test@example.test",
            username="visibility_test",
            password="SecurePassword123!",
        )

    def test_anonymous_visibility_request_is_rejected(self):

        response = self.client.get(
            "/api/v1/inventory/visibility/facility-stock/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_user_without_visibility_permission_is_denied(self):

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/v1/inventory/visibility/facility-stock/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )