from rest_framework import serializers

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
    StockMovement,
    StockReservation,
)


class InventoryBalanceSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="batch.medicine.generic_name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    warehouse_name = serializers.CharField(
        source="batch.warehouse.name",
        read_only=True,
    )

    location_code = serializers.CharField(
        source="batch.location.code",
        read_only=True,
    )

    quantity_available = serializers.DecimalField(
        max_digits=16,
        decimal_places=3,
        read_only=True,
    )

    class Meta:
        model = InventoryBalance
        fields = [
            "id",
            "batch",
            "medicine_name",
            "batch_number",
            "warehouse_name",
            "location_code",
            "quantity_on_hand",
            "quantity_reserved",
            "quantity_available",
            "last_movement_at",
            "updated_at",
        ]


class StockBatchSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    location_code = serializers.CharField(
        source="location.code",
        read_only=True,
    )

    balance = serializers.SerializerMethodField()

    class Meta:
        model = StockBatch
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "presentation",
            "warehouse",
            "warehouse_name",
            "location",
            "location_code",
            "batch_number",
            "manufacture_date",
            "expiry_date",
            "supplier",
            "supplier_reference",
            "received_date",
            "unit_cost",
            "currency",
            "status",
            "notes",
            "balance",
            "is_expired",
            "days_until_expiry",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_balance(self, obj):
        from apps.inventory.services import get_stock_balance

        balance = get_stock_balance(obj)

        return {
            key: str(value)
            for key, value in balance.items()
        }

    def validate(self, attrs):
        medicine = attrs.get(
            "medicine",
            self.instance.medicine if self.instance else None,
        )

        presentation = attrs.get(
            "presentation",
            self.instance.presentation if self.instance else None,
        )

        warehouse = attrs.get(
            "warehouse",
            self.instance.warehouse if self.instance else None,
        )

        location = attrs.get(
            "location",
            self.instance.location if self.instance else None,
        )

        if presentation and medicine:
            if presentation.medicine_id != medicine.pk:
                raise serializers.ValidationError({
                    "presentation": (
                        "Presentation does not belong to this medicine."
                    )
                })

        if warehouse and location:
            if location.zone.warehouse_id != warehouse.pk:
                raise serializers.ValidationError({
                    "location": (
                        "Storage location does not belong to this warehouse."
                    )
                })

        return attrs


class StockMovementSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="batch.medicine.generic_name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    performed_by_email = serializers.EmailField(
        source="performed_by.email",
        read_only=True,
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "batch",
            "medicine_name",
            "batch_number",
            "movement_type",
            "quantity",
            "reference_number",
            "reference_type",
            "source_warehouse",
            "destination_warehouse",
            "notes",
            "performed_by",
            "performed_by_email",
            "occurred_at",
            "created_at",
        ]

        read_only_fields = fields


class StockReservationSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="batch.medicine.generic_name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    class Meta:
        model = StockReservation
        fields = [
            "id",
            "batch",
            "medicine_name",
            "batch_number",
            "quantity",
            "reference_number",
            "purpose",
            "status",
            "reserved_by",
            "expires_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "reserved_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if attrs.get("quantity", 0) <= 0:
            raise serializers.ValidationError({
                "quantity": "Quantity must be positive."
            })

        return attrs