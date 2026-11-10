from rest_framework import serializers

from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    Medicine,
    TherapeuticCategory,
)


class TherapeuticCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TherapeuticCategory
        fields = [
            "id",
            "code",
            "name",
            "description",
            "parent",
            "is_active",
        ]


class DosageFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = DosageForm
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
        ]


class AdministrationRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdministrationRoute
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
        ]


class MeasurementUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasurementUnit
        fields = [
            "id",
            "code",
            "name",
            "symbol",
            "unit_type",
            "is_active",
        ]


class MedicineSerializer(serializers.ModelSerializer):
    therapeutic_category_name = serializers.CharField(
        source="therapeutic_category.name",
        read_only=True,
    )

    dosage_form_name = serializers.CharField(
        source="dosage_form.name",
        read_only=True,
    )

    administration_route_name = serializers.CharField(
        source="administration_route.name",
        read_only=True,
        allow_null=True,
    )

    strength_unit_name = serializers.CharField(
        source="strength_unit.name",
        read_only=True,
        allow_null=True,
    )

    dispensing_unit_name = serializers.CharField(
        source="dispensing_unit.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Medicine
        fields = [
            "id",
            "code",
            "generic_name",
            "brand_name",
            "description",
            "therapeutic_category",
            "therapeutic_category_name",
            "dosage_form",
            "dosage_form_name",
            "administration_route",
            "administration_route_name",
            "strength_value",
            "strength_unit",
            "strength_unit_name",
            "strength_display",
            "dispensing_unit",
            "dispensing_unit_name",
            "pack_size",
            "atc_code",
            "national_code",
            "is_essential",
            "is_controlled",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        value = value.strip().upper()

        queryset = Medicine.objects.filter(code__iexact=value)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "This medicine code is already registered."
            )

        return value

    def validate_atc_code(self, value):
        value = value.strip().upper()

        # ATC code validation is intentionally structural.
        # The catalog does not assume every country's list is identical.
        if value and len(value) > 7:
            raise serializers.ValidationError(
                "ATC code cannot exceed seven characters."
            )

        return value

    def validate(self, attrs):
        strength_value = attrs.get(
            "strength_value",
            self.instance.strength_value if self.instance else None,
        )

        strength_unit = attrs.get(
            "strength_unit",
            self.instance.strength_unit if self.instance else None,
        )

        if (strength_value is None) != (strength_unit is None):
            raise serializers.ValidationError(
                {
                    "strength_value": (
                        "Provide both strength value and strength unit."
                    ),
                    "strength_unit": ("Provide both strength value and strength unit."),
                }
            )

        pack_size = attrs.get(
            "pack_size",
            self.instance.pack_size if self.instance else None,
        )

        if pack_size is not None and pack_size <= 0:
            raise serializers.ValidationError(
                {"pack_size": "Pack size must be greater than zero."}
            )

        return attrs
