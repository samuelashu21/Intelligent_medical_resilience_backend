from django.contrib import admin

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
    StockMovement,
    StockReservation,
)


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = [
        "batch_number",
        "medicine",
        "warehouse",
        "location",
        "expiry_date",
        "status",
    ]

    list_filter = [
        "status",
        "warehouse",
        "expiry_date",
    ]

    search_fields = [
        "batch_number",
        "medicine__generic_name",
        "warehouse__name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]


@admin.register(InventoryBalance)
class InventoryBalanceAdmin(admin.ModelAdmin):
    list_display = [
        "batch",
        "quantity_on_hand",
        "quantity_reserved",
        "get_available",
        "last_movement_at",
    ]

    readonly_fields = [
        "batch",
        "quantity_on_hand",
        "quantity_reserved",
        "last_movement_at",
        "updated_at",
    ]

    def get_available(self, obj):
        return obj.quantity_available

    get_available.short_description = "Available"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "batch",
        "movement_type",
        "quantity",
        "reference_number",
        "performed_by",
        "occurred_at",
    ]

    list_filter = [
        "movement_type",
        "occurred_at",
    ]

    search_fields = [
        "batch__batch_number",
        "reference_number",
    ]

    readonly_fields = [
        field.name
        for field in StockMovement._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = [
        "reference_number",
        "batch",
        "quantity",
        "status",
        "reserved_by",
        "expires_at",
    ]

    list_filter = [
        "status",
        "created_at",
    ]

    search_fields = [
        "reference_number",
        "batch__batch_number",
    ]

    readonly_fields = [
        "id",
        "batch",
        "quantity",
        "reference_number",
        "purpose",
        "reserved_by",
        "created_at",
        "updated_at",
    ]