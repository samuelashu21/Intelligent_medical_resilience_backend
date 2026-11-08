from rest_framework import serializers

from apps.warehouses.models import (
    StorageLocation,
    StorageZone,
    Warehouse,
    WarehouseCapacitySnapshot,
    WarehouseManagerAssignment,
    WarehouseTemperatureReading,
)


class WarehouseSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
        allow_null=True,
    )

    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "code",
            "name",
            "warehouse_type",
            "organization",
            "organization_name",
            "facility",
            "facility_name",
            "description",
            "country",
            "country_name",
            "address",
            "city",
            "administrative_area",
            "postal_code",
            "latitude",
            "longitude",
            "phone",
            "email",
            "total_capacity",
            "capacity_unit",
            "status",
            "is_cold_chain_capable",
            "has_backup_power",
            "has_temperature_monitoring",
            "operating_hours",
            "notes",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]


class StorageZoneSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    class Meta:
        model = StorageZone
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class StorageLocationSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(
        source="zone.name",
        read_only=True,
    )

    warehouse_id = serializers.UUIDField(
        source="zone.warehouse_id",
        read_only=True,
    )

    class Meta:
        model = StorageLocation
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class WarehouseManagerAssignmentSerializer(
    serializers.ModelSerializer
):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = WarehouseManagerAssignment
        fields = [
            "id",
            "warehouse",
            "user",
            "user_email",
            "assigned_by",
            "is_active",
            "valid_from",
            "valid_until",
            "assigned_at",
        ]

        read_only_fields = [
            "id",
            "assigned_by",
            "assigned_at",
        ]

    def validate(self, attrs):
        valid_from = attrs.get(
            "valid_from",
            self.instance.valid_from if self.instance else None,
        )

        valid_until = attrs.get(
            "valid_until",
            self.instance.valid_until if self.instance else None,
        )

        if valid_from and valid_until and valid_until <= valid_from:
            raise serializers.ValidationError({
                "valid_until": "Must be after valid_from."
            })

        return attrs


class WarehouseTemperatureReadingSerializer(
    serializers.ModelSerializer
):
    classification = serializers.SerializerMethodField()

    class Meta:
        model = WarehouseTemperatureReading
        fields = [
            "id",
            "warehouse",
            "zone",
            "temperature",
            "humidity",
            "recorded_at",
            "source",
            "sensor_identifier",
            "recorded_by",
            "notes",
            "classification",
        ]

        read_only_fields = [
            "id",
            "recorded_by",
            "classification",
        ]

    def get_classification(self, obj):
        from apps.warehouses.services import classify_temperature_reading

        return classify_temperature_reading(obj)


class WarehouseCapacitySnapshotSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = WarehouseCapacitySnapshot
        fields = [
            "id",
            "warehouse",
            "measured_at",
            "used_capacity",
            "available_capacity",
            "capacity_unit",
            "recorded_by",
            "notes",
        ]

        read_only_fields = ["id", "recorded_by"]