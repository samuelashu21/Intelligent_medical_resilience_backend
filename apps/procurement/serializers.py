from rest_framework import serializers

from apps.procurement.models import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    SupplierQuotation,
    SupplierQuotationLine,
    PurchaseOrder,
    PurchaseOrderLine,
)


class PurchaseRequisitionLineSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    medicine_code = serializers.CharField(
        source="medicine.code",
        read_only=True,
    )

    class Meta:
        model = PurchaseRequisitionLine

        fields = [
            "id",
            "replenishment_line",
            "medicine",
            "medicine_name",
            "medicine_code",
            "quantity",
            "unit_code",
            "notes",
            "created_at",
        ]

        read_only_fields = fields


class PurchaseRequisitionSerializer(serializers.ModelSerializer):

    items = PurchaseRequisitionLineSerializer(
        many=True,
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    requester_email = serializers.CharField(
        source="requested_by.email",
        read_only=True,
    )

    class Meta:
        model = PurchaseRequisition

        fields = [
            "id",
            "requisition_number",
            "replenishment_request",
            "organization",
            "organization_name",
            "status",
            "justification",
            "requested_by",
            "requester_email",
            "submitted_by",
            "submitted_at",
            "approved_by",
            "approved_at",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class PurchaseRequisitionCreateSerializer(serializers.Serializer):

    replenishment_request = serializers.UUIDField()

    justification = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class QuotationLineInputSerializer(serializers.Serializer):

    requisition_line_id = serializers.UUIDField()

    quantity = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=0.001,
    )

    unit_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=4,
        min_value=0,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class SupplierQuotationCreateSerializer(serializers.Serializer):

    requisition = serializers.UUIDField()

    supplier = serializers.UUIDField()

    quotation_number = serializers.CharField(max_length=100)

    currency = serializers.CharField(
        min_length=3,
        max_length=3,
    )

    quotation_date = serializers.DateField(required=False)

    valid_until = serializers.DateField()

    delivery_days = serializers.IntegerField(min_value=0)

    payment_terms = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    delivery_terms = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    items = QuotationLineInputSerializer(
        many=True,
        allow_empty=False,
    )


class SupplierQuotationLineSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="requisition_line.medicine.generic_name",
        read_only=True,
    )

    line_total = serializers.DecimalField(
        max_digits=30,
        decimal_places=4,
        read_only=True,
    )

    class Meta:
        model = SupplierQuotationLine

        fields = [
            "id",
            "requisition_line",
            "medicine_name",
            "quantity",
            "unit_price",
            "line_total",
            "notes",
        ]

        read_only_fields = fields


class SupplierQuotationSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )

    quotation_total = serializers.SerializerMethodField()

    items = SupplierQuotationLineSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SupplierQuotation

        fields = [
            "id",
            "quotation_number",
            "requisition",
            "supplier",
            "supplier_name",
            "currency",
            "quotation_date",
            "valid_until",
            "payment_terms",
            "delivery_days",
            "delivery_terms",
            "status",
            "notes",
            "quotation_total",
            "items",
            "created_at",
        ]

        read_only_fields = fields

    def get_quotation_total(self, obj):
        from apps.procurement.services import (
            calculate_quotation_total,
        )

        return str(calculate_quotation_total(obj))


class PurchaseOrderLineSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = PurchaseOrderLine

        fields = [
            "id",
            "requisition_line",
            "medicine",
            "medicine_name",
            "quantity",
            "unit_code",
            "unit_price",
            "line_total",
        ]

        read_only_fields = fields


class PurchaseOrderSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )

    items = PurchaseOrderLineSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = PurchaseOrder

        fields = [
            "id",
            "order_number",
            "requisition",
            "quotation",
            "supplier",
            "supplier_name",
            "organization",
            "currency",
            "order_date",
            "expected_delivery_date",
            "status",
            "subtotal",
            "tax_amount",
            "shipping_amount",
            "total_amount",
            "payment_terms",
            "delivery_terms",
            "created_by",
            "approved_by",
            "approved_at",
            "sent_at",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class PurchaseOrderCreateSerializer(serializers.Serializer):

    quotation = serializers.UUIDField()

    tax_amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=4,
        min_value=0,
        required=False,
        default="0",
    )

    shipping_amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=4,
        min_value=0,
        required=False,
        default="0",
    )

    expected_delivery_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class SupplierSelectionSerializer(serializers.Serializer):

    justification = serializers.CharField(
        min_length=10,
    )


class PurchaseOrderAcknowledgeSerializer(serializers.Serializer):

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )
