from django.contrib import admin

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    Medicine,
    TherapeuticCategory,
)

from apps.medicines.models import (
    ATCClassification,
    Country,
    EssentialMedicineItem,
    EssentialMedicineList,
    MedicineEligibilityRule,
    MedicineImportBatch,
    MedicineImportRow,
    MedicineNationalCode,
    MedicinePresentation,
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


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["code", "name"]
    list_filter = ["is_active"]


@admin.register(ATCClassification)
class ATCClassificationAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "level",
        "parent",
        "is_active",
    ]

    search_fields = ["code", "name"]
    list_filter = ["level", "is_active"]
    autocomplete_fields = ["parent"]


@admin.register(EssentialMedicineList)
class EssentialMedicineListAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "country",
        "version",
        "effective_from",
        "effective_until",
        "is_active",
    ]

    search_fields = ["name", "version", "country__name"]
    list_filter = ["country", "is_active"]


@admin.register(EssentialMedicineItem)
class EssentialMedicineItemAdmin(admin.ModelAdmin):
    list_display = [
        "medicine",
        "essential_list",
        "level_of_care",
        "is_active",
    ]

    search_fields = [
        "medicine__generic_name",
        "essential_list__name",
    ]

    list_filter = [
        "level_of_care",
        "is_active",
    ]

    autocomplete_fields = [
        "medicine",
        "essential_list",
    ]


@admin.register(MedicineNationalCode)
class MedicineNationalCodeAdmin(admin.ModelAdmin):
    list_display = [
        "country",
        "medicine",
        "code",
        "is_primary",
        "is_active",
    ]

    search_fields = [
        "code",
        "medicine__generic_name",
    ]

    list_filter = ["country", "is_primary", "is_active"]


@admin.register(MedicinePresentation)
class MedicinePresentationAdmin(admin.ModelAdmin):
    list_display = [
        "presentation_code",
        "medicine",
        "description",
        "package_unit",
        "units_per_package",
        "is_active",
    ]

    search_fields = [
        "presentation_code",
        "description",
        "medicine__generic_name",
        "barcode",
    ]

    list_filter = ["is_active", "package_unit"]


@admin.register(MedicineEligibilityRule)
class MedicineEligibilityRuleAdmin(admin.ModelAdmin):
    list_display = [
        "medicine",
        "country",
        "organization",
        "facility",
        "is_allowed",
        "effective_from",
        "effective_until",
        "is_active",
    ]

    search_fields = ["medicine__generic_name", "reason"]
    list_filter = ["is_allowed", "country", "is_active"]


class MedicineImportRowInline(admin.TabularInline):
    model = MedicineImportRow
    extra = 0
    can_delete = False
    readonly_fields = [
        "row_number",
        "medicine_code",
        "status",
        "message",
        "source_data",
    ]


@admin.register(MedicineImportBatch)
class MedicineImportBatchAdmin(admin.ModelAdmin):
    list_display = [
        "filename",
        "status",
        "total_rows",
        "successful_rows",
        "failed_rows",
        "created_at",
    ]

    list_filter = ["status", "created_at"]
    search_fields = ["filename"]

    readonly_fields = [
        "uploaded_by",
        "filename",
        "status",
        "total_rows",
        "successful_rows",
        "failed_rows",
        "summary",
        "started_at",
        "completed_at",
        "created_at",
    ]

    inlines = [MedicineImportRowInline]    