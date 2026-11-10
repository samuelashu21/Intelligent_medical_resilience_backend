from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, Role
from apps.accounts.services import (
    assign_role,
    revoke_role_assignment,
)


class RoleAssignmentLifecycleTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            email="lifecycle.admin@example.com",
            username="lifecycle_admin",
            password="SecurePassword123!",
        )

        self.target = User.objects.create_user(
            email="lifecycle.user@example.com",
            username="lifecycle_user",
            password="SecurePassword123!",
        )

        self.role = Role.objects.create(
            code="LIFECYCLE_TEST_ROLE",
            name="Lifecycle Test Role",
        )

    def test_assign_role(self):
        assignment = assign_role(
            user=self.target,
            role=self.role,
            assigned_by=self.admin,
        )

        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.assigned_by, self.admin)

    def test_assign_role_with_expiration(self):
        expiry = timezone.now() + timedelta(days=30)

        assignment = assign_role(
            user=self.target,
            role=self.role,
            assigned_by=self.admin,
            valid_until=expiry,
        )

        self.assertEqual(assignment.valid_until, expiry)

    def test_revoke_assignment(self):
        assignment = assign_role(
            user=self.target,
            role=self.role,
            assigned_by=self.admin,
        )

        revoked = revoke_role_assignment(assignment)

        self.assertFalse(revoked.is_active)

    def test_assignment_can_be_reactivated(self):
        assignment = assign_role(
            user=self.target,
            role=self.role,
            assigned_by=self.admin,
        )

        revoke_role_assignment(assignment)

        reactivated = assign_role(
            user=self.target,
            role=self.role,
            assigned_by=self.admin,
        )

        self.assertTrue(reactivated.is_active)

    def test_inactive_user_cannot_receive_role(self):
        self.target.is_active = False
        self.target.save(update_fields=["is_active"])

        with self.assertRaises(Exception):
            assign_role(
                user=self.target,
                role=self.role,
                assigned_by=self.admin,
            )
