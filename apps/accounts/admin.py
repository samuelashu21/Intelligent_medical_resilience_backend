from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import (
    CustomUserCreationForm,
    CustomUserChangeForm,
)

from .models import (
    User,
    UserProfile,
    Role,
    AccessPermission,
    RolePermission,
    UserRole,
)


class UserProfileInline(admin.StackedInline):

    model = UserProfile

    can_delete = False

    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    add_form = CustomUserCreationForm

    form = CustomUserChangeForm

    model = User

    inlines = [UserProfileInline]

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )

    search_fields = (
        "email",
        "username",
        "first_name",
        "last_name",
    )

    ordering = ("email",)

    fieldsets = (
        (
            "Account Information",
            {
                "fields": (
                    "email",
                    "username",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            "Create Account",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "phone_number",
        "job_title",
        "preferred_language",
    )

    search_fields = (
        "user__email",
        "user__username",
        "phone_number",
    )


class RolePermissionInline(admin.TabularInline):

    model = RolePermission

    extra = 0

    autocomplete_fields = ["permission"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "is_system_role",
        "is_active",
    )

    list_filter = (
        "is_system_role",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    inlines = [RolePermissionInline]

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(AccessPermission)
class AccessPermissionAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "module",
        "is_active",
    )

    list_filter = (
        "module",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "role",
        "is_active",
        "assigned_by",
        "assigned_at",
        "organization",
        "facility",
        "valid_from",
        "valid_until",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "user__email",
        "role__name",
        "role__code",
    )

    readonly_fields = ("assigned_at",)

    autocomplete_fields = [
        "user",
        "role",
        "assigned_by",
    ]
