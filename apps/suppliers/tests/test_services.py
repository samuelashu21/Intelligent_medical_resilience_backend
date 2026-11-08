from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User

from apps.medicines.models import Country

from apps.suppliers.models import (
    Supplier,
    SupplierLicense,
    SupplierPerformanceRecord,
    SupplierStatus,
    SupplierType,
)

from apps.suppliers.services import (
    approve_supplier,
    get_supplier_performance,
    reject_supplier,
    suspend_supplier,
    verify_supplier_license,
)


class SupplierServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="supplier.admin@example.test",
            username="supplier_admin",
            password="SecurePassword123!",
        )

        self.country = Country.objects.create(
            code="ET",
            name="Ethiopia",
        )

        self.supplier = Supplier.objects.create(
            code="SERVICE-SUP-001",
            name="Service Test Supplier",
            supplier_type=SupplierType.DISTRIBUTOR,
            country=self.country,
            status=SupplierStatus.PENDING,
        )

    def test_approve_supplier(self):
        supplier = approve_supplier(
            supplier_id=self.supplier.pk,
            approved_by=self.user,
        )

        self.assertEqual(
            supplier.status,
            SupplierStatus.APPROVED,
        )

        self.assertEqual(
            supplier.approved_by,
            self.user,
        )

        self.assertIsNotNone(supplier.approved_at)

    def test_reject_supplier(self):
        supplier = reject_supplier(
            supplier_id=self.supplier.pk,
            rejected_by=self.user,
            reason="Incomplete registration.",
        )

        self.assertEqual(
            supplier.status,
            SupplierStatus.REJECTED,
        )

        self.assertIn(
            "Incomplete registration.",
            supplier.notes,
        )

    def test_suspend_approved_supplier(self):
        approve_supplier(
            supplier_id=self.supplier.pk,
            approved_by=self.user,
        )

        supplier = suspend_supplier(
            supplier_id=self.supplier.pk,
            reason="Compliance review.",
        )

        self.assertEqual(
            supplier.status,
            SupplierStatus.SUSPENDED,
        )

    def test_cannot_suspend_pending_supplier(self):
        with self.assertRaises(ValidationError):
            suspend_supplier(
                supplier_id=self.supplier.pk,
                reason="Test",
            )

    def test_verify_license(self):
        license_record = SupplierLicense.objects.create(
            supplier=self.supplier,
            license_type="BUSINESS",
            license_number="LIC-SERVICE-001",
            issuing_authority="Test Authority",
            expiry_date=date.today() + timedelta(days=365),
        )

        result = verify_supplier_license(
            license_id=license_record.pk,
            verified_by=self.user,
        )

        self.assertEqual(
            result.verification_status,
            "VERIFIED",
        )

        self.assertEqual(
            result.verified_by,
            self.user,
        )

    def test_performance_summary(self):
        SupplierPerformanceRecord.objects.create(
            supplier=self.supplier,
            reference_number="SERVICE-DEL-001",
            expected_delivery_date=date.today(),
            actual_delivery_date=date.today(),
            ordered_quantity=100,
            received_quantity=90,
            quality_accepted_quantity=85,
        )

        summary = get_supplier_performance(self.supplier)

        self.assertEqual(summary["delivery_records"], 1)
        self.assertEqual(summary["completed_deliveries"], 1)
        self.assertEqual(summary["on_time_rate"], 100.0)
        self.assertEqual(summary["fulfillment_rate"], 90.0)