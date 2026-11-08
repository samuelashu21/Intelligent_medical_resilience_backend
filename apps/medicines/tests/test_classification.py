from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.medicines.models import (
    ATCClassification,
    Country,
    DosageForm,
    EssentialMedicineItem,
    EssentialMedicineList,
    Medicine,
    MedicineEligibilityRule,
    MedicinePresentation,
    MeasurementUnit,
)

from apps.medicines.classification_services import (
    get_current_essential_medicines,
    get_medicine_eligibility,
    get_medicines_by_atc,
)


class ClassificationTests(TestCase):

    def setUp(self):
        self.level1 = ATCClassification.objects.create(
            code="N",
            name="Nervous system",
            level=1,
        )

        self.level2 = ATCClassification.objects.create(
            code="N02",
            name="Analgesics",
            level=2,
            parent=self.level1,
        )

        self.level3 = ATCClassification.objects.create(
            code="N02B",
            name="Other analgesics and antipyretics",
            level=3,
            parent=self.level2,
        )

        self.country = Country.objects.create(
            code="ET",
            name="Ethiopia",
        )

        self.tablet = DosageForm.objects.create(
            code="CLASS_TABLET",
            name="Classification Tablet",
        )

        self.mg = MeasurementUnit.objects.create(
            code="CLASS_MG",
            name="Classification Milligram",
            symbol="mg",
            unit_type="MASS",
        )

        self.tablet_unit = MeasurementUnit.objects.create(
            code="CLASS_TAB",
            name="Classification Tablet Unit",
            symbol="tablet",
            unit_type="COUNT",
        )

        self.medicine = Medicine.objects.create(
            code="CLASS-PAR-500",
            generic_name="Paracetamol",
            dosage_form=self.tablet,
            strength_value=500,
            strength_unit=self.mg,
            dispensing_unit=self.tablet_unit,
            atc_code="N02BE01",
            atc_classification=self.level3,
        )

    def test_atc_parent_level_validation(self):
        with self.assertRaises(ValidationError):
            ATCClassification.objects.create(
                code="N02BE",
                name="Invalid level",
                level=5,
                parent=self.level2,
            )

    def test_atc_hierarchy_medicine_search(self):
        results = get_medicines_by_atc(self.level1)

        self.assertTrue(
            results.filter(pk=self.medicine.pk).exists()
        )

    def test_country_code_normalization(self):
        country = Country(
            code="xx",
            name="Test Country",
        )

        country.save()

        self.assertEqual(country.code, "XX")

    def test_essential_medicine_list(self):
        essential_list = EssentialMedicineList.objects.create(
            country=self.country,
            name="Test Essential Medicines List",
            version="2026",
            effective_from=date(2026, 1, 1),
        )

        EssentialMedicineItem.objects.create(
            essential_list=essential_list,
            medicine=self.medicine,
            level_of_care="ALL",
        )

        results = get_current_essential_medicines(self.country)

        self.assertTrue(
            results.filter(pk=self.medicine.pk).exists()
        )

    def test_expired_essential_list_is_not_current(self):
        essential_list = EssentialMedicineList.objects.create(
            country=self.country,
            name="Expired Test List",
            version="2020",
            effective_from=date(2020, 1, 1),
            effective_until=date(2020, 12, 31),
        )

        EssentialMedicineItem.objects.create(
            essential_list=essential_list,
            medicine=self.medicine,
        )

        results = get_current_essential_medicines(self.country)

        self.assertFalse(
            results.filter(pk=self.medicine.pk).exists()
        )

    def test_global_restriction(self):
        MedicineEligibilityRule.objects.create(
            medicine=self.medicine,
            is_allowed=False,
            reason="Demonstration restriction",
            effective_from=date(2020, 1, 1),
        )

        result = get_medicine_eligibility(
            medicine=self.medicine,
            country=self.country,
        )

        self.assertFalse(result["allowed"])

    def test_presentation_package_quantity(self):
        presentation = MedicinePresentation.objects.create(
            medicine=self.medicine,
            presentation_code="CLASS-PAR-PACK-100",
            description="Paracetamol 500 mg, pack of 100 tablets",
            package_unit=self.tablet_unit,
            units_per_package=100,
        )

        self.assertEqual(
            presentation.units_per_package,
            100,
        )

    def test_invalid_presentation_quantity(self):
        presentation = MedicinePresentation(
            medicine=self.medicine,
            presentation_code="CLASS-INVALID-PACK",
            description="Invalid package",
            package_unit=self.tablet_unit,
            units_per_package=0,
        )

        with self.assertRaises(ValidationError):
            presentation.full_clean()