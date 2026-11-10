from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    """
    Integration tests for account authentication APIs.

    Covers:
    - Login
    - Invalid credentials
    - Inactive accounts
    - Current authenticated user
    - JWT refresh token rotation
    - Logout and token blacklisting
    - Password changes
    - Password validation
    """

    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            email="pharmacist@example.com",
            username="pharmacist",
            password="SecurePassword123!",
            first_name="Test",
            last_name="Pharmacist",
        )

        self.login_url = reverse(
            "accounts:login",
            kwargs={"version": "v1"},
        )

        self.refresh_url = reverse(
            "accounts:token-refresh",
            kwargs={"version": "v1"},
        )

        self.logout_url = reverse(
            "accounts:logout",
            kwargs={"version": "v1"},
        )

        self.me_url = reverse(
            "accounts:current-user",
            kwargs={"version": "v1"},
        )

        self.password_url = reverse(
            "accounts:change-password",
            kwargs={"version": "v1"},
        )

    # =========================================================
    # HELPER METHODS
    # =========================================================

    def login(self):
        """
        Authenticate the test user and return the response.
        """

        return self.client.post(
            self.login_url,
            {
                "email": "pharmacist@example.com",
                "password": "SecurePassword123!",
            },
            format="json",
        )

    def authenticate_client(self):
        """
        Authenticate the API client using an access token.
        """

        response = self.login()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        access = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        return response

    def assert_refresh_token_blacklisted(self, refresh_token):
        """
        Verify that a refresh token has been blacklisted.

        RefreshToken construction itself raises TokenError
        when blacklist checking is enabled and the token
        has already been blacklisted.
        """

        with self.assertRaises(TokenError):
            RefreshToken(refresh_token)

    # =========================================================
    # LOGIN TESTS
    # =========================================================

    def test_valid_login(self):
        response = self.login()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

        self.assertEqual(
            response.data["user"]["email"],
            "pharmacist@example.com",
        )

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

    # =========================================================
    # CURRENT USER TESTS
    # =========================================================

    def test_current_user_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_current_user_with_access_token(self):
        self.authenticate_client()

        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.assertEqual(
            response.data["email"],
            "pharmacist@example.com",
        )

        self.assertEqual(
            response.data["username"],
            "pharmacist",
        )

        self.assertIn("roles", response.data)
        self.assertIn("permissions", response.data)

    # =========================================================
    # REFRESH TOKEN TESTS
    # =========================================================

    def test_refresh_token_rotation(self):
        login_response = self.login()

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
            login_response.data,
        )

        old_refresh = login_response.data["refresh"]

        response = self.client.post(
            self.refresh_url,
            {
                "refresh": old_refresh,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        new_refresh = response.data["refresh"]

        # New refresh token must be different.
        self.assertNotEqual(
            old_refresh,
            new_refresh,
        )

        # The old refresh token must be blacklisted.
        self.assert_refresh_token_blacklisted(old_refresh)

        # The newly issued refresh token must remain valid.
        new_token = RefreshToken(new_refresh)

        self.assertIsNotNone(new_token)

    def test_blacklisted_refresh_token_cannot_be_reused(self):
        login_response = self.login()

        old_refresh = login_response.data["refresh"]

        first_response = self.client.post(
            self.refresh_url,
            {
                "refresh": old_refresh,
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
            first_response.data,
        )

        # Attempt to reuse the original refresh token.
        second_response = self.client.post(
            self.refresh_url,
            {
                "refresh": old_refresh,
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # =========================================================
    # LOGOUT TESTS
    # =========================================================

    def test_logout_blacklists_refresh_token(self):
        login_response = self.authenticate_client()

        refresh = login_response.data["refresh"]

        response = self.client.post(
            self.logout_url,
            {
                "refresh": refresh,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_205_RESET_CONTENT,
            response.data,
        )

        # Verify that the refresh token cannot be reconstructed.
        self.assert_refresh_token_blacklisted(refresh)

    def test_logout_requires_authentication(self):
        login_response = self.login()

        refresh = login_response.data["refresh"]

        response = self.client.post(
            self.logout_url,
            {
                "refresh": refresh,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_refresh_token(self):
        self.authenticate_client()

        response = self.client.post(
            self.logout_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # =========================================================
    # PASSWORD CHANGE TESTS
    # =========================================================

    def test_password_change(self):
        self.authenticate_client()

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
            response.data,
        )

        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password("AnotherSecurePassword456!"))

        self.assertFalse(self.user.check_password("SecurePassword123!"))

    def test_password_change_rejects_wrong_current_password(self):
        self.authenticate_client()

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

        self.user.refresh_from_db()

        # Original password must remain unchanged.
        self.assertTrue(self.user.check_password("SecurePassword123!"))

    def test_password_change_rejects_password_mismatch(self):
        self.authenticate_client()

        response = self.client.post(
            self.password_url,
            {
                "current_password": "SecurePassword123!",
                "new_password": "AnotherSecurePassword456!",
                "confirm_new_password": "DifferentPassword789!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_password_change_rejects_same_password(self):
        self.authenticate_client()

        response = self.client.post(
            self.password_url,
            {
                "current_password": "SecurePassword123!",
                "new_password": "SecurePassword123!",
                "confirm_new_password": "SecurePassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_password_change_requires_authentication(self):
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
            status.HTTP_401_UNAUTHORIZED,
        )
