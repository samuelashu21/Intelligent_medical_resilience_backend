from django.contrib import admin

from apps.logistics.receiving_models import (
    ReceivingRecord,
    ReceivingLine,
    ReceivingDiscrepancy,
    TransferReconciliation,
)


class ReceivingLineInline(admin.TabularInline):
    model = ReceivingLine
    extra = 0
    can_delete = False

    readonly_fields = [
        "shipment_line",
        "medicine",
        "batch",
        "dispatched_quantity",
        "physically_received_quantity",
        "accepted_quantity",
        "damaged_quantity",
        "expired_quantity",
        "other_rejected_quantity",
        "unit_code",
    ]


@admin.register(ReceivingRecord)
class ReceivingRecordAdmin(admin.ModelAdmin):

    list_display = [
        "receipt_number",
        "shipment",
        "recipient_facility",
        "receiving_warehouse",
        "status",
        "received_at",
        "approved_at",
        "posted_at",
    ]

    list_filter = [
        "status",
        "recipient_facility",
        "received_at",
    ]

    search_fields = [
        "receipt_number",
        "shipment__shipment_number",
    ]

    readonly_fields = [
        "receipt_number",
        "received_by",
        "submitted_by",
        "approved_by",
        "posted_by",
        "received_at",
        "submitted_at",
        "approved_at",
        "posted_at",
    ]

    inlines = [ReceivingLineInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReceivingLine)
class ReceivingLineAdmin(admin.ModelAdmin):

    list_display = [
        "receiving_record",
        "medicine",
        "batch",
        "dispatched_quantity",
        "physically_received_quantity",
        "accepted_quantity",
    ]

    readonly_fields = [
        field.name
        for field in ReceivingLine._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReceivingDiscrepancy)
class ReceivingDiscrepancyAdmin(admin.ModelAdmin):

    list_display = [
        "receiving_line",
        "discrepancy_type",
        "quantity",
        "status",
        "reported_at",
    ]

    list_filter = [
        "discrepancy_type",
        "status",
        "reported_at",
    ]

    readonly_fields = [
        "reported_by",
        "reported_at",
        "resolved_by",
        "resolved_at",
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TransferReconciliation)
class TransferReconciliationAdmin(admin.ModelAdmin):

    list_display = [
        "transfer",
        "receiving_record",
        "status",
        "dispatched_quantity_total",
        "accepted_quantity_total",
        "reconciled_at",
    ]

    list_filter = [
        "status",
        "reconciled_at",
    ]

    readonly_fields = [
        field.name
        for field in TransferReconciliation._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False    