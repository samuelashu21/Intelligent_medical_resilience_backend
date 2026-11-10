
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.replenishment.models import ReplenishmentApproval


class Command(BaseCommand):

    help = "Identify and escalate overdue replenishment approvals."

    def handle(self, *args, **options):

        now = timezone.now()

        overdue = (
            ReplenishmentApproval.objects.filter(
                status=ReplenishmentApproval.Status.PENDING,
                due_at__lt=now,
            )
            .select_related(
                "request",
                "workflow_stage",
                "organization",
            )
        )

        count = 0

        with transaction.atomic():

            for approval in overdue.select_for_update():

                approval.escalation_level += 1

                # Reschedule the approval deadline for one day later.
                approval.due_at = now + timedelta(days=1)

                approval.save(
                    update_fields=[
                        "escalation_level",
                        "due_at",
                    ]
                )

                count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Escalated {approval.request.request_number} "
                        f"at stage {approval.workflow_stage.name}."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {count} overdue approval stages."
            )
        )
