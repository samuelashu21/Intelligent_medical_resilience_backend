from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import (
    User,
    Role,
    AccessPermission,
)

from apps.accounts.services import assign_role


class UserManagementAPITests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            email="management.admin@example.com",
            username="management_admin",
            password="SecurePassword123!",
        )

        self.target = User.objects.create_user(
            email="management.target@example.com",
            username="management_target",
            password="SecurePassword123!",
        )

        self.role = Role.objects.create(
            code="USER_MANAGEMENT_TEST",
            name="User Management Test",
        )

        self.view_permission = AccessPermission.objects.create(
            code="users.view",
            name="View Users",
            module="users",
        )

        self.create_permission = AccessPermission.objects.create(
            code="users.create",
            name="Create Users",
            module="users",
        )

        self.role.permissions.add(
            self.view_permission,
            self.create_permission,
        )

        assign_role(
            user=self.admin,
            role=self.role,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.admin)}"
        )

    def test_list_users(self):
        response = self.client.get("/api/v1/accounts/users/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_create_user(self):
        payload = {
            "email": "new.user@example.com",
            "username": "new_user",
            "first_name": "New",
            "last_name": "User",
            "password": "StrongPassword123!",
        }

        response = self.client.post(
            "/api/v1/accounts/users/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertNotIn(
            "password",
            response.data,
        )

        self.assertTrue(User.objects.filter(email="new.user@example.com").exists())

    def test_user_without_token_cannot_access_users(self):
        self.client.credentials()

        response = self.client.get("/api/v1/accounts/users/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
