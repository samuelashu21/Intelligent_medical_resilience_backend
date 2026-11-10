from rest_framework import serializers

from apps.redistribution.optimization_models import (
    RedistributionOptimizationRun,
    RedistributionOptimizationAllocation,
    RedistributionTransportProfile,
)


class OptimizationRequestSerializer(serializers.Serializer):

    medicines = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )

    amc_months = serializers.IntegerField(
        min_value=1,
        max_value=12,
        default=3,
    )

    maximum_distance_km = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

    vehicle_capacity_units = serializers.DecimalField(
        max_digits=18,
        decimal_places=6,
        min_value=0.000001,
        default="1",
    )

    max_active_routes = serializers.IntegerField(
        min_value=1,
        max_value=10000,
        required=False,
        allow_null=True,
    )

    max_solver_seconds = serializers.IntegerField(
        min_value=1,
        max_value=300,
        default=30,
    )


class OptimizationAllocationSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    donor_name = serializers.CharField(
        source="donor_facility.name",
        read_only=True,
    )

    recipient_name = serializers.CharField(
        source="recipient_facility.name",
        read_only=True,
    )

    batch_number = serializers.CharField(
        source="batch.batch_number",
        read_only=True,
    )

    class Meta:

        model = RedistributionOptimizationAllocation

        fields = [
            "id",
            "medicine",
            "medicine_name",
            "donor_facility",
            "donor_name",
            "recipient_facility",
            "recipient_name",
            "batch",
            "batch_number",
            "quantity",
            "unit_code",
            "transport_capacity_units",
            "distance_km",
            "estimated_transport_cost",
            "status",
            "explanation",
        ]

        read_only_fields = fields


class OptimizationRunSerializer(serializers.ModelSerializer):

    allocations = OptimizationAllocationSerializer(
        many=True,
        read_only=True,
    )

    class Meta:

        model = RedistributionOptimizationRun

        fields = [
            "id",
            "run_number",
            "status",
            "solver_status",
            "objective_value",
            "solver_runtime_seconds",
            "total_allocated_capacity_units",
            "total_unmet_shortage_units",
            "total_distance_km",
            "total_estimated_transport_cost",
            "input_snapshot",
            "solver_metadata",
            "error_message",
            "algorithm_version",
            "created_at",
            "completed_at",
            "allocations",
        ]

        read_only_fields = fields


class TransportProfileSerializer(serializers.ModelSerializer):

    class Meta:

        model = RedistributionTransportProfile

        fields = [
            "id",
            "medicine",
            "inventory_unit_code",
            "capacity_units_per_inventory_unit",
            "is_active",
            "effective_from",
            "effective_until",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]
