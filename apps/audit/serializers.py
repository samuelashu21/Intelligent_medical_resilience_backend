
from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for audit event records.
    Provides related actor, organization, and facility information.
    """

    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
        allow_null=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
        allow_null=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditEvent

        fields = [
            "id",
            "actor",
            "actor_email",
            "category",
            "action",
            "target_type",
            "target_id",
            "description",
            "organization",
            "organization_name",
            "facility",
            "facility_name",
            "changes",
            "metadata",
            "ip_address",
            "created_at",
        ]

        read_only_fields = fields
