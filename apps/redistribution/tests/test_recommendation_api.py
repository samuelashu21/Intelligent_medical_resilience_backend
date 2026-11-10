from django.test import TestCase

from rest_framework.test import APIClient

from apps.accounts.models import User


class RedistributionRecommendationAPITests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            email="redistribution.test@example.test",
            username="redistribution_test",
            password="SecurePassword123!",
        )

    def test_anonymous_user_cannot_list_recommendations(self):

        response = self.client.get(
            "/api/v1/redistribution/recommendations/recommendations/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_anonymous_user_cannot_generate_recommendations(self):

        response = self.client.post(
            "/api/v1/redistribution/recommendations/recommendations/generate/",
            {
                "medicine": "00000000-0000-0000-0000-000000000001",
                "amc_months": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_user_without_permission_cannot_list_recommendations(self):

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/v1/redistribution/recommendations/recommendations/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )