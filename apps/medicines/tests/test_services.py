from django.test import TestCase

from apps.medicines.models import (
    DosageForm,
    Medicine,
)

from apps.medicines.services import search_medicines


class MedicineSearchTests(TestCase):

    def setUp(self):
        self.tablet = DosageForm.objects.create(
            code="SEARCH_TABLET",
            name="Search Tablet",
        )

        Medicine.objects.create(
            code="SEARCH-PAR",
            generic_name="Paracetamol",
            dosage_form=self.tablet,
            is_essential=True,
            atc_code="N02BE01",
        )

        Medicine.objects.create(
            code="SEARCH-AMX",
            generic_name="Amoxicillin",
            dosage_form=self.tablet,
            is_essential=True,
            atc_code="J01CA04",
        )

    def test_search_by_generic_name(self):
        results = search_medicines(search="Paracetamol")

        self.assertEqual(results.count(), 1)
        self.assertEqual(
            results.first().generic_name,
            "Paracetamol",
        )

    def test_search_by_atc_code(self):
        results = search_medicines(atc_code="N02")

        self.assertEqual(results.count(), 1)

    def test_filter_essential_medicines(self):
        results = search_medicines(essential=True)

        self.assertEqual(results.count(), 2)