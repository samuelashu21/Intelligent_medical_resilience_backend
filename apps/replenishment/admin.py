from django.contrib import admin

from apps.replenishment.models import (
    ReplenishmentRequest,
    ReplenishmentRequestLine,
)


class ReplenishmentRequestLineInline(admin.TabularInline):
    model = ReplenishmentRequestLine
    extra = 0
    can_delete = False

    readonly_fields = [
        "medicine",
        "requested_quantity",
        "recommended_quantity",
        "approved_quantity",
        "unit_code",
        "preferred_supplier",
    ]


@admin.register(ReplenishmentRequest)
class ReplenishmentRequestAdmin(admin.ModelAdmin):

    list_display = [
        "request_number",
        "facility",
        "priority",
        "source",
        "status",
        "requested_by",
        "requested_at",
    ]

    list_filter = [
        "status",
        "priority",
        "source",
        "organization",
    ]

    search_fields = [
        "request_number",
        "facility__name",
        "requested_by__email",
    ]

    readonly_fields = [
        "id",
        "request_number",
        "requested_at",
        "submitted_at",
        "approved_at",
        "rejected_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    ]

    inlines = [
        ReplenishmentRequestLineInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReplenishmentRequestLine)
class ReplenishmentRequestLineAdmin(admin.ModelAdmin):

    list_display = [
        "request",
        "medicine",
        "requested_quantity",
        "recommended_quantity",
        "approved_quantity",
        "unit_code",
    ]

    list_filter = [
        "medicine",
    ]

    search_fields = [
        "request__request_number",
        "medicine__generic_name",
        "medicine__code",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    def has_delete_permission(self, request, obj=None):
        return False