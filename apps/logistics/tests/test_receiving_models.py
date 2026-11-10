from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.logistics.receiving_models import (
    ReceivingLine,
)


class ReceivingLineValidationTests(TestCase):

    def test_accepted_quantity_cannot_exceed_physical_quantity(self):
        # Build a valid receiving line with your Phase 28 fixtures.
        line = self.make_receiving_line(
            dispatched="100",
            physical="80",
            accepted="90",
        )

        with self.assertRaises(ValidationError):
            line.full_clean()

    def test_accepted_quantity_cannot_exceed_dispatched(self):
        line = self.make_receiving_line(
            dispatched="100",
            physical="110",
            accepted="105",
        )

        with self.assertRaises(ValidationError):
            line.full_clean()

    def test_missing_quantity(self):
        line = self.make_receiving_line(
            dispatched="100",
            physical="90",
            accepted="90",
        )

        self.assertEqual(
            line.missing_quantity,
            Decimal("10"),
        )

    def test_excess_quantity(self):
        line = self.make_receiving_line(
            dispatched="100",
            physical="110",
            accepted="100",
        )

        self.assertEqual(
            line.excess_quantity,
            Decimal("10"),
        )

    def test_rejected_quantity(self):
        line = self.make_receiving_line(
            dispatched="100",
            physical="90",
            accepted="80",
        )

        self.assertEqual(
            line.rejected_quantity,
            Decimal("10"),
        )

    def make_receiving_line(
        self,
        *,
        dispatched,
        physical,
        accepted,
    ):
        """
        Use the real Phase 28 shipment and Phase 16 batch fixtures.
        The shipment line must match the medicine, batch,
        quantity and unit supplied to this receiving line.
        """
        raise NotImplementedError(
            "Connect this helper to your existing logistics test fixtures."
        )