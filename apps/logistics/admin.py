from django.contrib import admin

from apps.logistics.shipment_models import (
    Transporter,
    Vehicle,
    Shipment,
    ShipmentLine,
    ShipmentEvent,
    ShipmentDocument,
    ShipmentException,
)

from apps.logistics import receiving_admin

class ShipmentLineInline(admin.TabularInline):
    model = ShipmentLine
    extra = 0
    can_delete = False
    readonly_fields = [
        "transfer_line",
        "medicine",
        "batch",
        "dispatched_quantity",
        "unit_code",
    ]


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    can_delete = False
    readonly_fields = [
        "event_type",
        "description",
        "latitude",
        "longitude",
        "recorded_by",
        "event_time",
    ]


@admin.register(Transporter)
class TransporterAdmin(admin.ModelAdmin):

    list_display = [
        "code",
        "name",
        "organization",
        "phone",
        "status",
    ]

    list_filter = [
        "status",
        "organization",
    ]

    search_fields = [
        "code",
        "name",
        "phone",
    ]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):

    list_display = [
        "registration_number",
        "transporter",
        "vehicle_type",
        "status",
        "refrigerated",
    ]

    list_filter = [
        "status",
        "refrigerated",
    ]

    search_fields = [
        "registration_number",
        "transporter__name",
    ]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):

    list_display = [
        "shipment_number",
        "transfer",
        "transporter",
        "vehicle",
        "status",
        "dispatched_at",
        "estimated_delivery_at",
    ]

    list_filter = [
        "status",
        "transporter",
        "created_at",
    ]

    search_fields = [
        "shipment_number",
        "tracking_reference",
        "dispatch_reference",
    ]

    readonly_fields = [
        "shipment_number",
        "dispatched_at",
        "arrived_at",
        "delivered_at",
        "created_by",
        "created_at",
        "updated_at",
    ]

    inlines = [
        ShipmentLineInline,
        ShipmentEventInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ShipmentDocument)
class ShipmentDocumentAdmin(admin.ModelAdmin):

    list_display = [
        "shipment",
        "document_type",
        "reference_number",
        "uploaded_by",
        "uploaded_at",
    ]

    readonly_fields = [
        "uploaded_by",
        "uploaded_at",
    ]


@admin.register(ShipmentException)
class ShipmentExceptionAdmin(admin.ModelAdmin):

    list_display = [
        "shipment",
        "exception_type",
        "resolved",
        "reported_by",
        "reported_at",
    ]

    list_filter = [
        "exception_type",
        "resolved",
        "reported_at",
    ]

    readonly_fields = [
        "reported_by",
        "reported_at",
        "resolved_by",
        "resolved_at",
    ]