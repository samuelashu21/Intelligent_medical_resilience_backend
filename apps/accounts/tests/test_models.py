
from django.test import TestCase

from apps.accounts.models import User, UserProfile


class UserModelTests(TestCase):

    def test_create_user(self):

        user = User.objects.create_user(
            email="TEST@example.com",
            username="testuser",
            password="StrongPassword123!",
            first_name="Test",
            last_name="User",
        )

        self.assertEqual(
            user.email,
            "test@example.com",
        )

        self.assertTrue(
            user.check_password("StrongPassword123!")
        )

        self.assertFalse(user.is_staff)

        self.assertFalse(user.is_superuser)

        self.assertTrue(user.is_active)

    def test_user_has_uuid_primary_key(self):

        user = User.objects.create_user(
            email="uuid@example.com",
            username="uuiduser",
            password="StrongPassword123!",
        )

        self.assertIsNotNone(user.id)

        self.assertEqual(user.id.version, 4)

    def test_user_email_is_unique(self):

        User.objects.create_user(
            email="duplicate@example.com",
            username="firstuser",
            password="StrongPassword123!",
        )

        with self.assertRaises(Exception):

            User.objects.create_user(
                email="duplicate@example.com",
                username="seconduser",
                password="StrongPassword123!",
            )

    def test_create_superuser(self):

        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="StrongPassword123!",
        )

        self.assertTrue(admin_user.is_staff)

        self.assertTrue(admin_user.is_superuser)

        self.assertTrue(admin_user.is_active)

    def test_user_profile(self):

        user = User.objects.create_user(
            email="profile@example.com",
            username="profileuser",
            password="StrongPassword123!",
        )

        profile = UserProfile.objects.create(
            user=user,
            phone_number="+251900000000",
            job_title="Facility Pharmacist",
            preferred_language="am",
        )

        self.assertEqual(
            profile.user,
            user,
        )

        self.assertEqual(
            profile.preferred_language,
            "am",
        )
