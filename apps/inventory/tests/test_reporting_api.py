from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class StockReportingAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="stock.reporter@example.test",
            username="stock_reporter",
            password="SecurePassword123!",
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(
            "/api/v1/inventory/reports/dashboard/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_stock_report_requires_authentication(self):
        response = self.client.get(
            "/api/v1/inventory/reports/status/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_expiry_report_requires_authentication(self):
        response = self.client.get(
            "/api/v1/inventory/reports/expiry/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_csv_export_requires_authentication(self):
        response = self.client.get(
            "/api/v1/inventory/reports/export/csv/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )