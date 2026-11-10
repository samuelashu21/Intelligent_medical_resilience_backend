from django.contrib import admin

from apps.suppliers.models import (
    Supplier,
    SupplierAddress,
    SupplierContact,
    SupplierContract,
    SupplierLicense,
    SupplierMedicine,
    SupplierPerformanceRecord,
)


class SupplierContactInline(admin.TabularInline):
    model = SupplierContact
    extra = 0


class SupplierAddressInline(admin.TabularInline):
    model = SupplierAddress
    extra = 0


class SupplierLicenseInline(admin.TabularInline):
    model = SupplierLicense
    extra = 0


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "supplier_type",
        "country",
        "organization",
        "status",
        "created_at",
    ]

    list_filter = [
        "supplier_type",
        "status",
        "country",
    ]

    search_fields = [
        "code",
        "name",
        "registration_number",
        "tax_identification_number",
        "email",
    ]

    readonly_fields = [
        "created_by",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    ]

    inlines = [
        SupplierContactInline,
        SupplierAddressInline,
        SupplierLicenseInline,
    ]


@admin.register(SupplierContact)
class SupplierContactAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "supplier",
        "job_title",
        "email",
        "phone",
        "is_primary",
        "is_active",
    ]

    search_fields = [
        "full_name",
        "supplier__name",
        "email",
    ]

    list_filter = ["is_primary", "is_active"]


@admin.register(SupplierAddress)
class SupplierAddressAdmin(admin.ModelAdmin):
    list_display = [
        "supplier",
        "address_type",
        "city",
        "country",
        "is_primary",
        "is_active",
    ]

    list_filter = [
        "address_type",
        "country",
        "is_active",
    ]

    search_fields = ["supplier__name", "city"]


@admin.register(SupplierLicense)
class SupplierLicenseAdmin(admin.ModelAdmin):
    list_display = [
        "supplier",
        "license_type",
        "license_number",
        "expiry_date",
        "verification_status",
    ]

    list_filter = [
        "license_type",
        "verification_status",
    ]

    search_fields = [
        "supplier__name",
        "license_number",
        "issuing_authority",
    ]

    readonly_fields = [
        "verified_by",
        "verified_at",
        "created_at",
    ]


@admin.register(SupplierMedicine)
class SupplierMedicineAdmin(admin.ModelAdmin):
    list_display = [
        "supplier",
        "medicine",
        "presentation",
        "currency",
        "unit_price",
        "lead_time_days",
        "is_preferred",
        "is_active",
    ]

    list_filter = [
        "currency",
        "is_preferred",
        "is_active",
    ]

    search_fields = [
        "supplier__name",
        "medicine__generic_name",
        "supplier_product_code",
    ]


@admin.register(SupplierContract)
class SupplierContractAdmin(admin.ModelAdmin):
    list_display = [
        "contract_number",
        "supplier",
        "title",
        "start_date",
        "end_date",
        "status",
    ]

    list_filter = ["status", "currency"]

    search_fields = [
        "contract_number",
        "supplier__name",
        "title",
    ]

    readonly_fields = ["created_by", "created_at"]


@admin.register(SupplierPerformanceRecord)
class SupplierPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        "supplier",
        "reference_number",
        "expected_delivery_date",
        "actual_delivery_date",
        "ordered_quantity",
        "received_quantity",
        "quality_accepted_quantity",
    ]

    list_filter = [
        "expected_delivery_date",
        "actual_delivery_date",
    ]

    search_fields = [
        "supplier__name",
        "reference_number",
    ]

    readonly_fields = ["recorded_at"]
