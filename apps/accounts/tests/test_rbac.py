
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import (
    User,
    Role,
    AccessPermission,
    RolePermission,
    UserRole,
)

from apps.accounts.services import (
    assign_role,
    revoke_role,
    get_user_permissions,
    user_has_permission,
)


class RBACTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="pharmacist@example.com",
            username="pharmacist",
            password="StrongPassword123!",
        )

        self.role = Role.objects.create(
            code="FACILITY_PHARMACIST",
            name="Facility Pharmacist",
        )

        self.inventory_view = AccessPermission.objects.create(
            code="inventory.view",
            name="View inventory",
            module="inventory",
        )

        self.inventory_issue = AccessPermission.objects.create(
            code="inventory.issue",
            name="Issue inventory",
            module="inventory",
        )

        RolePermission.objects.create(
            role=self.role,
            permission=self.inventory_view,
        )

    def test_assign_role(self):

        assignment = assign_role(
            user=self.user,
            role=self.role,
        )

        self.assertTrue(assignment.is_active)

        self.assertEqual(
            assignment.user,
            self.user,
        )

    def test_assign_role_is_idempotent(self):

        first = assign_role(
            user=self.user,
            role=self.role,
        )

        second = assign_role(
            user=self.user,
            role=self.role,
        )

        self.assertEqual(first.pk, second.pk)

        self.assertEqual(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).count(),
            1,
        )

    def test_revoke_role(self):

        assign_role(
            user=self.user,
            role=self.role,
        )

        result = revoke_role(
            self.user,
            self.role,
        )

        self.assertTrue(result)

        self.assertFalse(
            UserRole.objects.get(
                user=self.user,
                role=self.role,
            ).is_active
        )

    def test_user_has_assigned_permission(self):

        assign_role(
            user=self.user,
            role=self.role,
        )

        self.assertTrue(
            user_has_permission(
                self.user,
                "inventory.view",
            )
        )

    def test_user_does_not_have_unassigned_permission(self):

        assign_role(
            user=self.user,
            role=self.role,
        )

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.issue",
            )
        )

    def test_inactive_assignment_grants_no_permission(self):

        assign_role(
            user=self.user,
            role=self.role,
        )

        revoke_role(
            self.user,
            self.role,
        )

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.view",
            )
        )

    def test_inactive_role_grants_no_permission(self):

        assign_role(
            user=self.user,
            role=self.role,
        )

        self.role.is_active = False

        self.role.save()

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.view",
            )
        )

    def test_expired_assignment_grants_no_permission(self):

        assignment = assign_role(
            user=self.user,
            role=self.role,
        )

        assignment.valid_until = (
            timezone.now() - timedelta(days=1)
        )

        assignment.save()

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.view",
            )
        )

    def test_superuser_has_all_permissions(self):

        superuser = User.objects.create_superuser(
            email="root@example.com",
            username="root",
            password="StrongPassword123!",
        )

        self.assertTrue(
            user_has_permission(
                superuser,
                "inventory.adjust",
            )
        )

    def test_inactive_user_has_no_permissions(self):

        assign_role(
            user=self.user,
            role=self.role,
        )

        self.user.is_active = False

        self.user.save()

        self.assertFalse(
            user_has_permission(
                self.user,
                "inventory.view",
            )
        )
