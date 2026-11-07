import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models 


from .managers import UserManager
from django.core.exceptions import ValidationError 

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


class Role(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=60,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    is_system_role = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    permissions = models.ManyToManyField(
        "accounts.AccessPermission",
        through="accounts.RolePermission",
        related_name="roles",
        blank=True,
    )

    class Meta:

        db_table = "accounts_role"

        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["code", "is_active"],
                name="role_code_active_idx",
            ),
        ]

    def __str__(self):

        return f"{self.name} ({self.code})"




class AccessPermission(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    module = models.CharField(
        max_length=80,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        db_table = "accounts_access_permission"

        ordering = ["module", "code"]

        indexes = [
            models.Index(
                fields=["module", "is_active"],
                name="permission_module_idx",
            ),
        ]

    def __str__(self):

        return self.code



class RolePermission(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    permission = models.ForeignKey(
        "accounts.AccessPermission",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    granted_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        db_table = "accounts_role_permission"

        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            ),
        ]

    def __str__(self):

        return f"{self.role.code} -> {self.permission.code}"



class UserRole(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )

    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.PROTECT,
        related_name="user_assignments",
    )

    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roles_assigned",
    )

    is_active = models.BooleanField(
        default=True,
    )

    valid_from = models.DateTimeField(
        null=True,
        blank=True,
    )

    valid_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_role_assignments",
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_role_assignments",
    )

    class Meta:

        db_table = "accounts_user_role"

        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=models.Q(
                    organization__isnull=True,
                    facility__isnull=True,
                ),
                name="unique_global_user_role",
            ),
            models.UniqueConstraint(
                fields=["user", "role", "organization"],
                condition=models.Q(
                    organization__isnull=False,
                    facility__isnull=True,
                ),
                name="unique_org_user_role",
            ),
            models.UniqueConstraint(
                fields=["user", "role", "facility"],
                condition=models.Q(
                    facility__isnull=False,
                ),
                name="unique_facility_user_role",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="user_role_active_idx",
            ),
            models.Index(
                fields=["organization", "is_active"],
                name="userrole_org_active_idx",
            ),
            models.Index(
                fields=["facility", "is_active"],
                name="userrole_fac_active_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.organization_id and self.facility_id:
            if self.facility.organization_id != self.organization_id:
                raise ValidationError(
                    {
                        "facility": (
                            "The facility must belong directly to the "
                            "selected organization."
                        )
                    }
                ) 

        if self.facility_id and not self.facility.is_active:
            raise ValidationError(
                {"facility": "Cannot assign a role to an inactive facility."}
            )

        if self.organization_id and not self.organization.is_active:
            raise ValidationError(
                {"organization": "Cannot assign a role to an inactive organization."}
            )

        if self.role_id and not self.role.is_active:
            raise ValidationError(
                {"role": "Cannot assign an inactive role."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.user.email} - {self.role.code}"