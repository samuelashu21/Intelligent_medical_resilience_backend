from decimal import Decimal

from django.test import TestCase

from apps.inventory.visibility_services import (
    get_facility_stock_summary,
    get_facility_medicine_availability,
    get_facility_medicine_stock,
)


class StockVisibilityServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        Create two facilities, warehouses, a medicine,
        stock batches, and inventory balances.

        Reuse the fixture patterns from your existing
        inventory and batch lifecycle tests.
        """
        pass

    def test_facility_stock_summary(self):
        result = get_facility_stock_summary(
            facility_id=self.facility_a.pk,
        )

        self.assertEqual(
            result["on_hand"],
            Decimal("500"),
        )

        self.assertEqual(
            result["reserved"],
            Decimal("100"),
        )

        self.assertEqual(
            result["available"],
            Decimal("400"),
        )

    def test_medicine_availability(self):
        result = get_facility_medicine_availability(
            facility_id=self.facility_a.pk,
            medicine_id=self.medicine.pk,
        )

        self.assertEqual(
            result["available"],
            Decimal("400"),
        )

    def test_expired_batch_is_excluded(self):
        result = get_facility_medicine_availability(
            facility_id=self.facility_a.pk,
            medicine_id=self.medicine.pk,
        )

        # Add an expired batch with a large quantity
        # in the fixture and verify that it is not counted.
        self.assertEqual(
            result["available"],
            Decimal("400"),
        )

    def test_facility_stock_aggregation(self):
        rows = list(
            get_facility_medicine_stock(
                medicine_id=self.medicine.pk,
                facility_ids=[
                    self.facility_a.pk,
                    self.facility_b.pk,
                ],
            )
        )

        self.assertEqual(len(rows), 2)