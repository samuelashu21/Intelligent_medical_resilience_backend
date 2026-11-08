from django.contrib import admin

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    Medicine,
    TherapeuticCategory,
)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "generic_name",
        "brand_name",
        "dosage_form",
        "strength_display",
        "atc_code",
        "is_essential",
        "is_active",
    ]

    list_filter = [
        "is_active",
        "is_essential",
        "is_controlled",
        "dosage_form",
        "therapeutic_category",
    ]

    search_fields = [
        "code",
        "generic_name",
        "brand_name",
        "atc_code",
        "national_code",
    ]

    autocomplete_fields = [
        "therapeutic_category",
        "dosage_form",
        "administration_route",
        "strength_unit",
        "dispensing_unit",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    list_per_page = 50


@admin.register(TherapeuticCategory)
class TherapeuticCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "parent",
        "is_active",
    ]

    search_fields = [
        "code",
        "name",
    ]

    list_filter = ["is_active"]

    autocomplete_fields = ["parent"]


@admin.register(DosageForm)
class DosageFormAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["code", "name"]
    list_filter = ["is_active"]


@admin.register(AdministrationRoute)
class AdministrationRouteAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["code", "name"]
    list_filter = ["is_active"]


@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "symbol",
        "unit_type",
        "is_active",
    ]

    search_fields = ["code", "name", "symbol"]
    list_filter = ["unit_type", "is_active"]