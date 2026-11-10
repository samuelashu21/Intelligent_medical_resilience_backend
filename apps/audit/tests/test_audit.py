from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event


class AuditEventTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="audit.admin@example.com",
            username="audit_admin",
            password="SecurePassword123!",
        )

    def test_create_audit_event(self):
        event = record_audit_event(
            actor=self.user,
            category="USER",
            action="USER_CREATED",
            target_type="User",
            target_id="user-001",
            description="Created test user.",
            changes={
                "is_active": {
                    "before": None,
                    "after": True,
                }
            },
        )

        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.category, "USER")
        self.assertEqual(event.action, "USER_CREATED")
        self.assertEqual(event.target_id, "user-001")

    def test_audit_event_can_survive_actor_deletion(self):
        event = record_audit_event(
            actor=self.user,
            category="USER",
            action="USER_CREATED",
            target_type="User",
            target_id="user-002",
        )

        self.user.delete()

        event.refresh_from_db()

        self.assertIsNone(event.actor_id)

    def test_audit_changes_default_to_empty_dictionary(self):
        event = record_audit_event(
            actor=self.user,
            category="SYSTEM",
            action="TEST_EVENT",
            target_type="System",
        )

        self.assertEqual(event.changes, {})
        self.assertEqual(event.metadata, {})
