from rest_framework import serializers

from apps.medicines.models import (
    ATCClassification,
    Country,
    EssentialMedicineItem,
    EssentialMedicineList,
    MedicineEligibilityRule,
    MedicineNationalCode,
    MedicinePresentation,
)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "code", "name", "is_active"]
        read_only_fields = ["id"]


class ATCClassificationSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(
        source="parent.code",
        read_only=True,
    )

    class Meta:
        model = ATCClassification
        fields = [
            "id",
            "code",
            "name",
            "level",
            "parent",
            "parent_code",
            "description",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        parent = attrs.get(
            "parent",
            self.instance.parent if self.instance else None,
        )
        level = attrs.get(
            "level",
            self.instance.level if self.instance else None,
        )

        if parent and level != parent.level + 1:
            raise serializers.ValidationError(
                {"level": "Classification level must be one greater than its parent."}
            )

        if level == 1 and parent:
            raise serializers.ValidationError(
                {"parent": "Level 1 cannot have a parent."}
            )

        return attrs


class EssentialMedicineListSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
    )

    class Meta:
        model = EssentialMedicineList
        fields = [
            "id",
            "country",
            "country_name",
            "name",
            "version",
            "effective_from",
            "effective_until",
            "source_reference",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class EssentialMedicineItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = EssentialMedicineItem
        fields = [
            "id",
            "essential_list",
            "medicine",
            "medicine_name",
            "level_of_care",
            "notes",
            "is_active",
        ]
        read_only_fields = ["id"]


class MedicineNationalCodeSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
    )

    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = MedicineNationalCode
        fields = [
            "id",
            "country",
            "country_name",
            "medicine",
            "medicine_name",
            "code",
            "description",
            "is_primary",
            "is_active",
        ]
        read_only_fields = ["id"]


class MedicinePresentationSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    package_unit_name = serializers.CharField(
        source="package_unit.name",
        read_only=True,
    )

    class Meta:
        model = MedicinePresentation
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "presentation_code",
            "description",
            "package_unit",
            "package_unit_name",
            "units_per_package",
            "barcode",
            "manufacturer",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_units_per_package(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Units per package must be greater than zero."
            )
        return value


class MedicineEligibilityRuleSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    class Meta:
        model = MedicineEligibilityRule
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "country",
            "organization",
            "facility",
            "is_allowed",
            "reason",
            "effective_from",
            "effective_until",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        facility = attrs.get(
            "facility",
            self.instance.facility if self.instance else None,
        )

        organization = attrs.get(
            "organization",
            self.instance.organization if self.instance else None,
        )

        if facility and not organization:
            raise serializers.ValidationError(
                {"organization": "Organization is required for facility-level rules."}
            )

        if facility and organization:
            if facility.organization_id != organization.id:
                raise serializers.ValidationError(
                    {"facility": "Facility does not belong to this organization."}
                )

        start = attrs.get(
            "effective_from",
            self.instance.effective_from if self.instance else None,
        )

        end = attrs.get(
            "effective_until",
            self.instance.effective_until if self.instance else None,
        )

        if start and end and end < start:
            raise serializers.ValidationError(
                {"effective_until": "End date cannot be earlier than start date."}
            )

        return attrs
