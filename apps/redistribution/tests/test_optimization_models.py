from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.redistribution.optimization_models import (
    RedistributionTransportProfile,
    RedistributionOptimizationRun,
    RedistributionOptimizationAllocation,
)


class RedistributionOptimizationModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        Reuse the organization, facility, and medicine fixtures
        already defined in your redistribution test suite.
        """
        pass

    def test_transport_conversion_must_be_positive(self):

        profile = RedistributionTransportProfile(
            medicine=self.medicine,
            inventory_unit_code="TABLET",
            capacity_units_per_inventory_unit=Decimal("0"),
        )

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_transport_profile_end_date_must_be_valid(self):

        profile = RedistributionTransportProfile(
            medicine=self.medicine,
            inventory_unit_code="TABLET",
            capacity_units_per_inventory_unit=Decimal("0.00001"),
            effective_from=timezone.localdate(),
            effective_until=timezone.localdate() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_run_number_is_generated(self):

        run = RedistributionOptimizationRun.objects.create(
            generated_by=self.user,
        )

        self.assertTrue(
            run.run_number.startswith("OPT-")
        )

    def test_allocation_cannot_transfer_to_same_facility(self):

        run = RedistributionOptimizationRun.objects.create(
            generated_by=self.user,
        )

        allocation = RedistributionOptimizationAllocation(
            optimization_run=run,
            medicine=self.medicine,
            donor_facility=self.facility_a,
            recipient_facility=self.facility_a,
            batch=self.batch,
            quantity=Decimal("10"),
            unit_code="TABLET",
            transport_capacity_units=Decimal("0.0001"),
        )

        with self.assertRaises(ValidationError):
            allocation.full_clean()