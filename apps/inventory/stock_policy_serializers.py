from rest_framework import serializers

from apps.inventory.models import StockPolicy


class StockPolicySerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
        allow_null=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    created_by_email = serializers.CharField(
        source="created_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StockPolicy

        fields = [
            "id",
            "policy_level",
            "organization",
            "organization_name",
            "facility",
            "facility_name",
            "medicine",
            "medicine_name",
            "minimum_stock",
            "maximum_stock",
            "safety_stock",
            "buffer_stock",
            "lead_time_days",
            "review_period_days",
            "minimum_order_quantity",
            "is_essential",
            "status",
            "effective_from",
            "effective_until",
            "notes",
            "created_by",
            "created_by_email",
            "updated_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        policy_level = attrs.get(
            "policy_level",
            instance.policy_level if instance else "FACILITY",
        )

        organization = attrs.get(
            "organization",
            instance.organization if instance else None,
        )

        facility = attrs.get(
            "facility",
            instance.facility if instance else None,
        )

        minimum_stock = attrs.get(
            "minimum_stock",
            instance.minimum_stock if instance else 0,
        )

        maximum_stock = attrs.get(
            "maximum_stock",
            instance.maximum_stock if instance else None,
        )

        if not organization:
            raise serializers.ValidationError(
                {"organization": "Organization is required."}
            )

        if maximum_stock is None:
            raise serializers.ValidationError(
                {"maximum_stock": "Maximum stock is required."}
            )

        if maximum_stock < minimum_stock:
            raise serializers.ValidationError(
                {
                    "maximum_stock": (
                        "Maximum stock must be greater than or equal "
                        "to minimum stock."
                    )
                }
            )

        if policy_level == StockPolicy.PolicyLevel.FACILITY:
            if not facility:
                raise serializers.ValidationError(
                    {"facility": ("Facility is required for a facility policy.")}
                )

            if facility.organization_id != organization.pk:
                raise serializers.ValidationError(
                    {"facility": ("Facility must belong to the selected organization.")}
                )

        elif policy_level == StockPolicy.PolicyLevel.ORGANIZATION:
            if facility:
                raise serializers.ValidationError(
                    {
                        "facility": (
                            "Organization default policies cannot select " "a facility."
                        )
                    }
                )

        else:
            raise serializers.ValidationError({"policy_level": "Invalid policy level."})

        if self.instance and self.instance.status == "ACTIVE":
            raise serializers.ValidationError(
                "Deactivate an active policy before editing it."
            )

        return attrs
