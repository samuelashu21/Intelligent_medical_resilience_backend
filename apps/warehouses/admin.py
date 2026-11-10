from django.contrib import admin

from apps.warehouses.models import (
    StorageLocation,
    StorageZone,
    Warehouse,
    WarehouseCapacitySnapshot,
    WarehouseManagerAssignment,
    WarehouseTemperatureReading,
)


class StorageZoneInline(admin.TabularInline):
    model = StorageZone
    extra = 0


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "warehouse_type",
        "organization",
        "facility",
        "status",
        "is_cold_chain_capable",
    ]

    list_filter = [
        "warehouse_type",
        "status",
        "organization",
        "is_cold_chain_capable",
    ]

    search_fields = [
        "code",
        "name",
        "city",
        "administrative_area",
    ]

    readonly_fields = [
        "created_by",
        "created_at",
        "updated_at",
    ]

    inlines = [StorageZoneInline]


@admin.register(StorageZone)
class StorageZoneAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "warehouse",
        "storage_type",
        "capacity",
        "is_active",
    ]

    list_filter = [
        "storage_type",
        "is_active",
        "warehouse",
    ]

    search_fields = [
        "code",
        "name",
        "warehouse__name",
    ]


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "zone",
        "aisle",
        "rack",
        "shelf",
        "bin_number",
        "is_active",
    ]

    list_filter = ["is_active", "zone"]

    search_fields = [
        "code",
        "name",
        "zone__name",
        "zone__warehouse__name",
    ]


@admin.register(WarehouseManagerAssignment)
class WarehouseManagerAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "warehouse",
        "user",
        "assigned_by",
        "is_active",
        "valid_from",
        "valid_until",
    ]

    list_filter = ["is_active", "warehouse"]

    search_fields = [
        "warehouse__name",
        "user__email",
    ]


@admin.register(WarehouseTemperatureReading)
class WarehouseTemperatureReadingAdmin(admin.ModelAdmin):
    list_display = [
        "warehouse",
        "zone",
        "temperature",
        "humidity",
        "source",
        "recorded_at",
    ]

    list_filter = ["source", "warehouse"]

    search_fields = [
        "warehouse__name",
        "sensor_identifier",
    ]

    readonly_fields = ["recorded_at"]


@admin.register(WarehouseCapacitySnapshot)
class WarehouseCapacitySnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "warehouse",
        "used_capacity",
        "available_capacity",
        "capacity_unit",
        "measured_at",
    ]

    list_filter = ["warehouse", "capacity_unit"]

    readonly_fields = ["measured_at"]
