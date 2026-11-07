from rest_framework import serializers

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

 
class OrganizationUnitTypeSerializer(serializers.ModelSerializer):

    parent_type_name = serializers.CharField(
        source="parent_type.name",
        read_only=True,
    )
 
    class Meta:
        model = OrganizationUnitType
        fields = [
            "id",
            "code",
            "name",
            "description",
            "level",
            "parent_type",
            "parent_type_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationSerializer(serializers.ModelSerializer):

    organization_type_name = serializers.CharField(
        source="organization_type.name",
        read_only=True,
    )

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "code",
            "organization_type",
            "organization_type_name",
            "parent",
            "parent_name",
            "description",
            "address",
            "contact_email",
            "contact_phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance

        parent = attrs.get(
            "parent",
            instance.parent if instance else None,
        )

        organization_type = attrs.get(
            "organization_type",
            instance.organization_type if instance else None,
        )

        if parent and organization_type:
            if parent.organization_type.level >= organization_type.level:
                raise serializers.ValidationError({
                    "parent": "Parent must have a higher hierarchy level."
                })

            expected_parent_type = organization_type.parent_type

            if (
                expected_parent_type
                and parent.organization_type_id != expected_parent_type.id
            ):
                raise serializers.ValidationError({
                    "parent": "Parent organization has an incompatible type."
                })

        if instance and parent:
            if parent.pk == instance.pk:
                raise serializers.ValidationError({
                    "parent": "An organization cannot be its own parent."
                })

            descendants = instance.get_descendants()

            if any(item.pk == parent.pk for item in descendants):
                raise serializers.ValidationError({
                    "parent": "Circular organization relationships are not allowed."
                })

        return attrs