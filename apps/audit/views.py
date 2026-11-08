from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_active_role_assignments,
    get_user_accessible_facility_ids,
    get_user_accessible_organization_ids,
)

from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = AuditEventSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    required_permissions = ["audit.view"]

    def get_queryset(self):
        user = self.request.user

        queryset = AuditEvent.objects.select_related(
            "actor",
            "organization",
            "facility",
        )

        if user.is_superuser:
            return queryset

        assignments = get_active_role_assignments(user)

        global_access = assignments.filter(
            organization__isnull=True,
            facility__isnull=True,
        ).exists()

        if global_access:
            return queryset

        organization_ids = get_user_accessible_organization_ids(user)
        facility_ids = get_user_accessible_facility_ids(user)

        return queryset.filter(
            Q(actor=user)
            | Q(organization_id__in=organization_ids)
            | Q(facility_id__in=facility_ids)
        ).distinct()
  
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        category = self.request.query_params.get("category")
        action = self.request.query_params.get("action")
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")

        if category:
            queryset = queryset.filter(category=category)

        if action:
            queryset = queryset.filter(action=action)

        if target_type:
            queryset = queryset.filter(target_type=target_type)

        if target_id:
            queryset = queryset.filter(target_id=target_id)

        return queryset 