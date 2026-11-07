from rest_framework import serializers

from apps.facilities.models import Facility, FacilityType


class FacilityTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = FacilityType
        fields = [
            "id",
            "code", 
            "name",
            "description",
            "is_active",
            "created_at",
        ]  
        read_only_fields = ["id", "created_at"]


class FacilitySerializer(serializers.ModelSerializer):

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    facility_type_name = serializers.CharField(
        source="facility_type.name",
        read_only=True,
    )

    class Meta:
        model = Facility
        fields = [ 
            "id",
            "name",
            "code",
            "facility_type",
            "facility_type_name",
            "organization",
            "organization_name",
            "address",
            "contact_person",
            "contact_email",
            "contact_phone",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = attrs.get(
            "organization",
            self.instance.organization if self.instance else None,
        )

        if organization and not organization.is_active:
            raise serializers.ValidationError({
                "organization": "Select an active organization."
            })

        facility_type = attrs.get(
            "facility_type",
            self.instance.facility_type if self.instance else None,
        )

        if facility_type and not facility_type.is_active:
            raise serializers.ValidationError({
                "facility_type": "Select an active facility type."
            })

        return attrs