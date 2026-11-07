from django.contrib import admin

from apps.facilities.models import Facility, FacilityType


@admin.register(FacilityType)
class FacilityTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "is_active",
    ]

    list_filter = ["is_active"]

    search_fields = ["name", "code"]


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "facility_type",
        "organization",
        "is_active",
    ]

    list_filter = [
        "facility_type",
        "organization",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
        "organization__name",
    ]

    autocomplete_fields = [
        "organization",
        "facility_type",
    ]