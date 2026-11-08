
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.audit.services import record_audit_event


class Command(BaseCommand):
    help = "Deactivate role assignments that have expired."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()

        expired_assignments = (
            UserRole.objects
            .select_for_update(of=("self",))
            .filter(
                is_active=True,
                valid_until__isnull=False,
                valid_until__lte=now,
            )
            .select_related(
                "user",
                "role",
                "organization",
                "facility",
            )
        )

        count = 0

        for assignment in expired_assignments:
            assignment.is_active = False
            assignment.save(update_fields=["is_active"])

            record_audit_event(
                actor=None,
                category="ROLE",
                action="ROLE_EXPIRED",
                target_type="UserRole",
                target_id=assignment.pk,
                description=(
                    f"Expired {assignment.role.code} for "
                    f"{assignment.user.email}."
                ),
                organization=assignment.organization,
                facility=assignment.facility,
                changes={
                    "is_active": {
                        "before": True,
                        "after": False,
                    }
                },
                metadata={
                    "expiration_processed_at": now.isoformat(),
                },
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Deactivated {count} expired role assignment(s)."
            )
        )
