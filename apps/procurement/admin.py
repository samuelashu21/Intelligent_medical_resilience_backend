from django.contrib import admin

from apps.procurement.models import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    SupplierQuotation,
    SupplierQuotationLine,
    PurchaseOrder,
    PurchaseOrderLine,
)


class PurchaseRequisitionLineInline(
    admin.TabularInline
):
    model = PurchaseRequisitionLine
    extra = 0
    can_delete = False
    readonly_fields = [
        "id",
        "replenishment_line",
        "medicine",
        "quantity",
        "unit_code",
        "created_at",
    ]


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(admin.ModelAdmin):

    list_display = [
        "requisition_number",
        "organization",
        "status",
        "requested_by",
        "submitted_at",
        "approved_at",
    ]

    list_filter = [
        "status",
        "organization",
        "created_at",
    ]

    search_fields = [
        "requisition_number",
        "replenishment_request__request_number",
        "organization__name",
    ]

    readonly_fields = [
        "id",
        "requisition_number",
        "created_at",
        "updated_at",
        "submitted_at",
        "approved_at",
    ]

    inlines = [
        PurchaseRequisitionLineInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False


class SupplierQuotationLineInline(
    admin.TabularInline
):
    model = SupplierQuotationLine
    extra = 0
    can_delete = False
    readonly_fields = [
        "id",
        "requisition_line",
        "quantity",
        "unit_price",
        "line_total",
        "notes",
    ]


@admin.register(SupplierQuotation)
class SupplierQuotationAdmin(admin.ModelAdmin):

    list_display = [
        "quotation_number",
        "requisition",
        "supplier",
        "currency",
        "valid_until",
        "delivery_days",
        "status",
    ]

    list_filter = [
        "status",
        "currency",
        "quotation_date",
    ]

    search_fields = [
        "quotation_number",
        "supplier__name",
        "requisition__requisition_number",
    ]

    readonly_fields = [
        "id",
        "created_at",
    ]

    inlines = [
        SupplierQuotationLineInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False


class PurchaseOrderLineInline(
    admin.TabularInline
):
    model = PurchaseOrderLine
    extra = 0
    can_delete = False
    readonly_fields = [
        "id",
        "requisition_line",
        "medicine",
        "quantity",
        "unit_code",
        "unit_price",
        "line_total",
    ]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):

    list_display = [
        "order_number",
        "supplier",
        "organization",
        "currency",
        "total_amount",
        "status",
        "order_date",
        "expected_delivery_date",
    ]

    list_filter = [
        "status",
        "currency",
        "organization",
        "order_date",
    ]

    search_fields = [
        "order_number",
        "supplier__name",
        "requisition__requisition_number",
    ]

    readonly_fields = [
        "id",
        "order_number",
        "subtotal",
        "total_amount",
        "approved_by",
        "approved_at",
        "sent_at",
        "created_at",
        "updated_at",
    ]

    inlines = [
        PurchaseOrderLineInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False