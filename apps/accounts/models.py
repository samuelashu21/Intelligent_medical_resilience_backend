
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    email = models.EmailField(
        unique=True,
        max_length=254,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "accounts_user"
        ordering = ["email"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def save(self, *args, **kwargs):

        if self.email:
            self.email = self.email.strip().lower()

        super().save(*args, **kwargs)

    def __str__(self):

        return self.email

    @property
    def full_name(self):

        return self.get_full_name().strip() or self.username




class UserProfile(models.Model):

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("am", "Amharic"),
    ]

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="profile",
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
    )

    job_title = models.CharField(
        max_length=150,
        blank=True,
    )

    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="en",
    )

    timezone = models.CharField(
        max_length=60,
        default="Africa/Addis_Ababa",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounts_user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):

        return f"Profile: {self.user.email}"
