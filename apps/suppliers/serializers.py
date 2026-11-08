from rest_framework import serializers

from apps.suppliers.models import (
    Supplier,
    SupplierAddress,
    SupplierContact,
    SupplierContract,
    SupplierLicense,
    SupplierMedicine,
    SupplierPerformanceRecord,
)


class SupplierSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    class Meta:
        model = Supplier
        fields = [
            "id",
            "code",
            "name",
            "supplier_type",
            "registration_number",
            "tax_identification_number",
            "country",
            "country_name",
            "organization",
            "organization_name",
            "website",
            "email",
            "phone",
            "address",
            "status",
            "notes",
            "created_by",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]


class SupplierContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierContact
        fields = [
            "id",
            "supplier",
            "full_name",
            "job_title",
            "email",
            "phone",
            "is_primary",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SupplierAddressSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
    )

    class Meta:
        model = SupplierAddress
        fields = [
            "id",
            "supplier",
            "address_type",
            "label",
            "address_line",
            "city",
            "administrative_area",
            "postal_code",
            "country",
            "country_name",
            "latitude",
            "longitude",
            "is_primary",
            "is_active",
        ]
        read_only_fields = ["id"]


class SupplierLicenseSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupplierLicense
        fields = [
            "id",
            "supplier",
            "license_type",
            "license_number",
            "issuing_authority",
            "issue_date",
            "expiry_date",
            "document",
            "verification_status",
            "verified_by",
            "verified_at",
            "is_expired",
            "notes",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "verification_status",
            "verified_by",
            "verified_at",
            "created_at",
        ]


class SupplierMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.generic_name",
        read_only=True,
    )

    presentation_description = serializers.CharField(
        source="presentation.description",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = SupplierMedicine
        fields = [
            "id",
            "supplier",
            "medicine",
            "medicine_name",
            "presentation",
            "presentation_description",
            "supplier_product_code",
            "currency",
            "unit_price",
            "lead_time_days",
            "minimum_order_quantity",
            "is_preferred",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_currency(self, value):
        value = value.upper().strip()

        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError(
                "Currency must be a three-letter ISO currency code."
            )

        return value


class SupplierContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierContract
        fields = [
            "id",
            "supplier",
            "contract_number",
            "title",
            "description",
            "start_date",
            "end_date",
            "currency",
            "contract_value",
            "status",
            "document",
            "created_by",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_by",
            "created_at",
        ]

    def validate(self, attrs):
        start = attrs.get(
            "start_date",
            self.instance.start_date if self.instance else None,
        )

        end = attrs.get(
            "end_date",
            self.instance.end_date if self.instance else None,
        )

        if start and end and end < start:
            raise serializers.ValidationError({
                "end_date": "Contract end date must follow start date."
            })

        return attrs


class SupplierPerformanceRecordSerializer(
    serializers.ModelSerializer
):
    on_time = serializers.ReadOnlyField()
    fulfillment_rate = serializers.ReadOnlyField()
    quality_acceptance_rate = serializers.ReadOnlyField()

    class Meta:
        model = SupplierPerformanceRecord
        fields = [
            "id",
            "supplier",
            "contract",
            "reference_number",
            "expected_delivery_date",
            "actual_delivery_date",
            "ordered_quantity",
            "received_quantity",
            "quality_accepted_quantity",
            "quality_issue_count",
            "fulfillment_rate",
            "quality_acceptance_rate",
            "on_time",
            "notes",
            "recorded_at",
        ]

        read_only_fields = ["id", "recorded_at"]