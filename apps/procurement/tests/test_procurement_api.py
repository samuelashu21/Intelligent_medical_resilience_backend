from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class ProcurementAPITests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            email="procurement.api@example.test",
            username="procurement_api",
            password="SecurePassword123!",
        )

    def test_anonymous_requisition_list_requires_authentication(self):

        response = self.client.get(
            "/api/v1/procurement/requisitions/"
        )

        self.assertEqual(response.status_code, 401)

    def test_anonymous_quotation_list_requires_authentication(self):

        response = self.client.get(
            "/api/v1/procurement/quotations/"
        )

        self.assertEqual(response.status_code, 401)

    def test_anonymous_purchase_order_list_requires_authentication(self):

        response = self.client.get(
            "/api/v1/procurement/purchase-orders/"
        )

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_without_permission_is_denied(self):

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/v1/procurement/requisitions/"
        )

        self.assertEqual(response.status_code, 403)