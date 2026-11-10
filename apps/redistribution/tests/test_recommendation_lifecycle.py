from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
    RecommendationStatus,
    RecommendationPriority,
)

from apps.accounts.models import User


class RecommendationLifecycleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        Reuse the existing facility, organization, and medicine
        fixtures from your redistribution tests.
        """
        pass

    def test_recommendation_number_is_generated(self):

        recommendation = self.create_recommendation()

        self.assertTrue(
            recommendation.recommendation_number.startswith("RR-")
        )

    def test_donor_and_recipient_must_differ(self):

        recommendation = self.create_recommendation()

        recommendation.recipient_facility = (
            recommendation.donor_facility
        )

        with self.assertRaises(ValidationError):
            recommendation.full_clean()

    def test_recommendation_quantity_must_be_positive(self):

        recommendation = self.create_recommendation()

        recommendation.recommended_quantity = 0

        with self.assertRaises(ValidationError):
            recommendation.full_clean()

    def test_recommendation_has_pending_status(self):

        recommendation = self.create_recommendation()

        self.assertEqual(
            recommendation.status,
            RecommendationStatus.PENDING,
        )

    def create_recommendation(self):
        """
        Implement using your existing Phase 9 organization,
        Phase 9 facility, and Phase 11 medicine fixtures.
        """

        return RedistributionRecommendation.objects.create(
            medicine=self.medicine,
            donor_facility=self.facility_a,
            recipient_facility=self.facility_b,
            donor_organization=self.facility_a.organization,
            recipient_organization=self.facility_b.organization,
            recommended_quantity="100",
            unit_code="TABLET",
            donor_available_before="1000",
            recipient_available_before="50",
            donor_available_after="900",
            recipient_available_after="150",
            priority=RecommendationPriority.HIGH,
            priority_score="70",
            explanation={
                "reason": "Recipient is below its operational target."
            },
            expires_at=timezone.now() + timedelta(days=2),
        )