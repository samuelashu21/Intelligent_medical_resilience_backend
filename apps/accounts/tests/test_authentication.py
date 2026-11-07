from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


class AuthenticationAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="pharmacist@example.com",
            username="pharmacist",
            password="SecurePassword123!",
            first_name="Test",
            last_name="Pharmacist",
        )

        self.login_url = reverse("accounts:login", kwargs={"version": "v1"})
        self.refresh_url = reverse("accounts:token-refresh", kwargs={"version": "v1"})
        self.logout_url = reverse("accounts:logout", kwargs={"version": "v1"})
        self.me_url = reverse("accounts:current-user", kwargs={"version": "v1"})
        self.password_url = reverse("accounts:change-password", kwargs={"version": "v1"})

    def login(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "pharmacist@example.com",
                "password": "SecurePassword123!",
            },
            format="json",
        )

        return response

    def test_valid_login(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

    def test_invalid_password(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "pharmacist@example.com",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unknown_email(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "unknown@example.com",
                "password": "SecurePassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.login_url,
            {
                "email": "pharmacist@example.com",
                "password": "SecurePassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_current_user_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_current_user_with_access_token(self):
        login_response = self.login()
        access = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["email"],
            "pharmacist@example.com",
        )

    def test_refresh_token_rotation(self):
        login_response = self.login()
        old_refresh = login_response.data["refresh"]

        response = self.client.post(
            self.refresh_url,
            {"refresh": old_refresh},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.assertNotEqual(
            old_refresh,
            response.data["refresh"],
        )

        # The original refresh token must no longer be usable.
        old_token = RefreshToken(old_refresh)

        with self.assertRaises(TokenError):
            old_token.check_blacklist()

    def test_logout_blacklists_refresh_token(self):
        login_response = self.login()

        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        response = self.client.post(
            self.logout_url,
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_205_RESET_CONTENT,
        )

        token = RefreshToken(refresh)

        with self.assertRaises(TokenError):
            token.check_blacklist()

    def test_password_change(self):
        login_response = self.login()
        access = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        response = self.client.post(
            self.password_url,
            {
                "current_password": "SecurePassword123!",
                "new_password": "AnotherSecurePassword456!",
                "confirm_new_password": "AnotherSecurePassword456!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password("AnotherSecurePassword456!")
        )

    def test_password_change_rejects_wrong_current_password(self):
        login_response = self.login()
        access = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        response = self.client.post(
            self.password_url,
            {
                "current_password": "WrongPassword123!",
                "new_password": "AnotherSecurePassword456!",
                "confirm_new_password": "AnotherSecurePassword456!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )