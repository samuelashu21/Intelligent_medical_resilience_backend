from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
    RecommendationStatus,
)


class Command(BaseCommand):

    help = "Expire outdated pending redistribution recommendations."

    def handle(self, *args, **options):

        now = timezone.now()

        expired = RedistributionRecommendation.objects.filter(
            status=RecommendationStatus.PENDING,
            expires_at__isnull=False,
            expires_at__lte=now,
        )

        count = expired.update(
            status=RecommendationStatus.EXPIRED,
            updated_at=now,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Expired {count} redistribution recommendations.")
        )
