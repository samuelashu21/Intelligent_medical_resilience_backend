from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.medicines.models import (
    Country,
    DosageForm,
    Medicine,
    MedicinePresentation,
    MeasurementUnit,
)

from apps.suppliers.models import (
    Supplier,
    SupplierAddress,
    SupplierContact,
    SupplierContract,
    SupplierLicense,
    SupplierMedicine,
    SupplierPerformanceRecord,
    SupplierStatus,
    SupplierType,
)


class SupplierModelTests(TestCase):

    def setUp(self):
        self.country = Country.objects.create(
            code="ET",
            name="Ethiopia",
        )

        self.supplier = Supplier.objects.create(
            code="TEST-SUP-001",
            name="Test Pharmaceutical Supplier",
            supplier_type=SupplierType.DISTRIBUTOR,
            country=self.country,
            status=SupplierStatus.PENDING,
        )

        self.tablet = DosageForm.objects.create(
            code="SUP_TEST_TABLET",
            name="Supplier Test Tablet",
        )

        self.tablet_unit = MeasurementUnit.objects.create(
            code="SUP_TEST_TABLET_UNIT",
            name="Supplier Test Tablet Unit",
            symbol="tablet",
            unit_type="COUNT",
        )

        self.medicine = Medicine.objects.create(
            code="SUP_TEST_PAR",
            generic_name="Paracetamol",
            dosage_form=self.tablet,
        )

        self.presentation = MedicinePresentation.objects.create(
            medicine=self.medicine,
            presentation_code="SUP_TEST_PAR_100",
            description="Paracetamol pack of 100 tablets",
            package_unit=self.tablet_unit,
            units_per_package=100,
        )

    def test_supplier_creation(self):
        self.assertEqual(
            self.supplier.status,
            SupplierStatus.PENDING,
        )

    def test_supplier_code_normalization(self):
        supplier = Supplier(
            code=" test-sup-002 ",
            name="Another Supplier",
            supplier_type=SupplierType.WHOLESALER,
        )

        supplier.save()

        self.assertEqual(supplier.code, "TEST-SUP-002")

    def test_contact_creation(self):
        contact = SupplierContact.objects.create(
            supplier=self.supplier,
            full_name="Test Contact",
            email="contact@example.test",
            is_primary=True,
        )

        self.assertEqual(contact.supplier, self.supplier)

    def test_only_one_primary_contact(self):
        SupplierContact.objects.create(
            supplier=self.supplier,
            full_name="Primary Contact",
            is_primary=True,
        )

        with self.assertRaises(Exception):
            SupplierContact.objects.create(
                supplier=self.supplier,
                full_name="Second Primary Contact",
                is_primary=True,
            )

    def test_address_coordinate_validation(self):
        address = SupplierAddress(
            supplier=self.supplier,
            address_type="WAREHOUSE",
            address_line="Test address",
            latitude=Decimal("100.000000"),
            longitude=Decimal("37.000000"),
        )

        with self.assertRaises(ValidationError):
            address.full_clean()

    def test_license_date_validation(self):
        license_record = SupplierLicense(
            supplier=self.supplier,
            license_type="BUSINESS",
            license_number="LIC-001",
            issuing_authority="Test Authority",
            issue_date=date(2026, 5, 1),
            expiry_date=date(2026, 4, 1),
        )

        with self.assertRaises(ValidationError):
            license_record.full_clean()

    def test_supplier_medicine_creation(self):
        offering = SupplierMedicine.objects.create(
            supplier=self.supplier,
            medicine=self.medicine,
            presentation=self.presentation,
            currency="ETB",
            unit_price=Decimal("250.00"),
            lead_time_days=14,
            minimum_order_quantity=10,
        )

        self.assertEqual(
            offering.medicine,
            self.medicine,
        )

    def test_presentation_must_match_medicine(self):
        another_medicine = Medicine.objects.create(
            code="SUP_TEST_AMX",
            generic_name="Amoxicillin",
            dosage_form=self.tablet,
        )

        offering = SupplierMedicine(
            supplier=self.supplier,
            medicine=another_medicine,
            presentation=self.presentation,
        )

        with self.assertRaises(ValidationError):
            offering.full_clean()

    def test_contract_date_validation(self):
        contract = SupplierContract(
            supplier=self.supplier,
            contract_number="TEST-CONTRACT-001",
            title="Invalid Contract",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 1),
        )

        with self.assertRaises(ValidationError):
            contract.full_clean()

    def test_performance_metrics(self):
        record = SupplierPerformanceRecord.objects.create(
            supplier=self.supplier,
            reference_number="DELIVERY-001",
            expected_delivery_date=date.today(),
            actual_delivery_date=date.today(),
            ordered_quantity=100,
            received_quantity=90,
            quality_accepted_quantity=85,
        )

        self.assertEqual(record.fulfillment_rate, 90.0)

        self.assertAlmostEqual(
            record.quality_acceptance_rate,
            94.444444,
            places=4,
        )

        self.assertTrue(record.on_time)
