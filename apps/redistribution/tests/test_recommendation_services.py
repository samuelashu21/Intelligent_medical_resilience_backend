from decimal import Decimal

from django.test import SimpleTestCase

from apps.redistribution.recommendation_services import (
    calculate_stock_coverage_days,
    calculate_haversine_distance,
    calculate_recommendation_priority,
    calculate_donor_transferable_quantity,
    calculate_recipient_shortage,
    allocate_donor_batches_fefo,
)


class RedistributionCalculationTests(SimpleTestCase):

    def test_stock_coverage(self):

        result = calculate_stock_coverage_days(
            available=Decimal("300"),
            daily_demand=Decimal("10"),
        )

        self.assertEqual(
            result,
            Decimal("30.00"),
        )

    def test_stock_coverage_without_demand(self):

        result = calculate_stock_coverage_days(
            available=Decimal("300"),
            daily_demand=None,
        )

        self.assertIsNone(result)

    def test_haversine_distance_same_coordinates(self):

        distance = calculate_haversine_distance(
            latitude_a=9.03,
            longitude_a=38.74,
            latitude_b=9.03,
            longitude_b=38.74,
        )

        self.assertEqual(
            distance,
            Decimal("0.00"),
        )

    def test_haversine_distance_missing_coordinates(self):

        distance = calculate_haversine_distance(
            latitude_a=None,
            longitude_a=None,
            latitude_b=9.03,
            longitude_b=38.74,
        )

        self.assertIsNone(distance)

    def test_priority_is_critical_for_imminent_stockout(self):

        profile = {
            "coverage_days": Decimal("2.00"),
            "available": Decimal("20"),
            "policy_configured": True,
            "minimum_stock": Decimal("100"),
            "maximum_stock": Decimal("500"),
            "safety_stock": Decimal("50"),
            "daily_demand": Decimal("10"),
            "policy": None,
        }

        result = calculate_recommendation_priority(
            recipient_profile=profile,
            distance_km=Decimal("10"),
            essential_medicine=True,
        )

        self.assertEqual(
            result["priority"],
            "CRITICAL",
        )

    def test_missing_distance_does_not_crash_priority(self):

        profile = {
            "coverage_days": Decimal("10"),
            "available": Decimal("50"),
            "policy_configured": True,
            "minimum_stock": Decimal("100"),
        }

        result = calculate_recommendation_priority(
            recipient_profile=profile,
            distance_km=None,
            essential_medicine=False,
        )

        self.assertGreaterEqual(
            result["score"],
            Decimal("0"),
        )

    def test_donor_without_policy_has_no_transferable_quantity(self):

        profile = {
            "policy_configured": False,
            "available": Decimal("1000"),
            "minimum_stock": None,
            "safety_stock": None,
            "daily_demand": Decimal("10"),
            "policy": None,
        }

        result = calculate_donor_transferable_quantity(
            profile
        )

        self.assertEqual(
            result,
            Decimal("0"),
        )

    def test_recipient_without_policy_has_no_calculated_shortage(self):

        profile = {
            "policy_configured": False,
            "available": Decimal("0"),
            "minimum_stock": None,
            "safety_stock": None,
            "daily_demand": Decimal("10"),
            "policy": None,
        }

        result = calculate_recipient_shortage(
            profile
        )

        self.assertEqual(
            result,
            Decimal("0"),
        )