from rest_framework import serializers


class FacilityStockVisibilitySerializer(serializers.Serializer):

    medicine_id = serializers.UUIDField()
    medicine_code = serializers.CharField()
    medicine_name = serializers.CharField()

    facility_id = serializers.UUIDField()
    facility_code = serializers.CharField()
    facility_name = serializers.CharField()

    organization_id = serializers.UUIDField()
    organization_name = serializers.CharField()

    on_hand = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    reserved = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    available = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )


class FacilityMedicineAvailabilitySerializer(serializers.Serializer):

    facility_id = serializers.UUIDField()
    medicine_id = serializers.UUIDField()

    on_hand = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    reserved = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    available = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )


class FacilityStockClassificationSerializer(serializers.Serializer):

    facility_id = serializers.UUIDField()
    medicine_id = serializers.UUIDField()

    on_hand = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    reserved = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    available = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    status = serializers.CharField()

    minimum_stock = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
        allow_null=True,
    )

    maximum_stock = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
        allow_null=True,
    )

    surplus_quantity = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    shortage_quantity = serializers.DecimalField(
        max_digits=20,
        decimal_places=3,
    )

    policy_configured = serializers.BooleanField()
