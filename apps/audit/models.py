import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    EVENT_CATEGORIES = [
        ("USER", "User Management"),
        ("ROLE", "Role Management"),
        ("ORGANIZATION", "Organization Management"),
        ("FACILITY", "Facility Management"),
        ("AUTHENTICATION", "Authentication"),
        ("SECURITY", "Security"),
        ("SYSTEM", "System"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    category = models.CharField(
        max_length=30,
        choices=EVENT_CATEGORIES,
        db_index=True,
    )

    action = models.CharField(
        max_length=100,
        db_index=True,
    )

    target_type = models.CharField(
        max_length=100,
    )

    target_id = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    changes = models.JSONField(
        default=dict,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["category", "created_at"],
                name="audit_category_time_idx",
            ),
            models.Index(
                fields=["actor", "created_at"],
                name="audit_actor_time_idx",
            ),
            models.Index(
                fields=["target_type", "target_id"],
                name="audit_target_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="audit_org_time_idx",
            ),
            models.Index(
                fields=["facility", "created_at"],
                name="audit_fac_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.category}: {self.action} ({self.created_at})"
