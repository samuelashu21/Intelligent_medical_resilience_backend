from django.contrib import admin

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)


@admin.register(OrganizationUnitType)
class OrganizationUnitTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "level",
        "parent_type",
        "is_active",
    ]

    list_filter = [
        "level",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
    ]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "organization_type",
        "parent",
        "is_active",
    ]

    list_filter = [
        "organization_type",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
    ]

    autocomplete_fields = [
        "organization_type",
        "parent",
    ]