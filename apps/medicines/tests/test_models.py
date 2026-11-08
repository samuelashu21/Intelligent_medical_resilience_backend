from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    Medicine,
    TherapeuticCategory,
)


class MedicineModelTests(TestCase):

    def setUp(self):
        self.tablet = DosageForm.objects.create(
            code="TEST_TABLET",
            name="Test Tablet",
        )

        self.oral = AdministrationRoute.objects.create(
            code="TEST_ORAL",
            name="Test Oral",
        )

        self.mg = MeasurementUnit.objects.create(
            code="TEST_MG",
            name="Test Milligram",
            symbol="mg",
            unit_type="MASS",
        )

        self.tablet_unit = MeasurementUnit.objects.create(
            code="TEST_TAB_UNIT",
            name="Test Tablet Unit",
            symbol="tablet",
            unit_type="COUNT",
        )

        self.category = TherapeuticCategory.objects.create(
            code="TEST_ANALGESICS",
            name="Test Analgesics",
        )

    def test_create_medicine(self):
        medicine = Medicine.objects.create(
            code="TEST-PAR-500",
            generic_name="Paracetamol",
            dosage_form=self.tablet,
            administration_route=self.oral,
            strength_value=Decimal("500"),
            strength_unit=self.mg,
            strength_display="500 mg",
            dispensing_unit=self.tablet_unit,
            therapeutic_category=self.category,
            is_essential=True,
        )

        self.assertEqual(medicine.generic_name, "Paracetamol")
        self.assertTrue(medicine.is_essential)

    def test_strength_must_be_positive(self):
        medicine = Medicine(
            code="TEST-INVALID-STRENGTH",
            generic_name="Test Medicine",
            dosage_form=self.tablet,
            strength_value=Decimal("0"),
            strength_unit=self.mg,
        )

        with self.assertRaises(ValidationError):
            medicine.full_clean()

    def test_strength_value_requires_unit(self):
        medicine = Medicine(
            code="TEST-MISSING-UNIT",
            generic_name="Test Medicine",
            dosage_form=self.tablet,
            strength_value=Decimal("500"),
        )

        with self.assertRaises(ValidationError):
            medicine.full_clean()

    def test_pack_size_must_be_positive(self):
        medicine = Medicine(
            code="TEST-INVALID-PACK",
            generic_name="Test Medicine",
            dosage_form=self.tablet,
            pack_size=0,
        )

        with self.assertRaises(ValidationError):
            medicine.full_clean()

    def test_medicine_is_not_deleted_by_deactivation(self):
        medicine = Medicine.objects.create(
            code="TEST-DEACTIVATE",
            generic_name="Test Medicine",
            dosage_form=self.tablet,
        )

        medicine.is_active = False
        medicine.save()

        self.assertTrue(
            Medicine.objects.filter(
                pk=medicine.pk
            ).exists()
        ) 