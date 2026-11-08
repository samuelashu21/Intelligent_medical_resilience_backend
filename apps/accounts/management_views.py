
from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_active_role_assignments,
    get_user_accessible_facility_ids,
    get_user_accessible_organization_ids,
)
from apps.accounts.serializers import (
    AdministrativeUserCreateSerializer,
    AdministrativeUserSerializer,
)
from apps.audit.services import record_audit_event


User = get_user_model()


class AdministrativeUserViewSet(viewsets.ModelViewSet):
    """
    Administrative user-management endpoints.

    Users are listed only when they have an assignment within
    the administrator's accessible scope, or are globally assigned.
    """

    queryset = User.objects.all()

    permission_classes = [
        HasSystemPermission,
    ]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["users.create"]

        elif self.action in ["update", "partial_update"]:
            self.required_permissions = ["users.update"]

        elif self.action == "deactivate":
            self.required_permissions = ["users.deactivate"]

        elif self.action == "activate":
            self.required_permissions = ["users.update"]

        else:
            self.required_permissions = ["users.view"]

        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return AdministrativeUserCreateSerializer

        return AdministrativeUserSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return User.objects.all().order_by("email")

        assignments = get_active_role_assignments(user)

        global_access = assignments.filter(
            organization__isnull=True,
            facility__isnull=True,
        ).exists()

        if global_access:
            return User.objects.all().order_by("email")

        organization_ids = get_user_accessible_organization_ids(user)
        facility_ids = get_user_accessible_facility_ids(user)

        return (
            User.objects.filter(
                role_assignments__is_active=True,
            ).filter(
                role_assignments__organization_id__in=organization_ids
            )
            | User.objects.filter(
                role_assignments__is_active=True,
                role_assignments__facility_id__in=facility_ids,
            )
        ).distinct().order_by("email")

    def perform_create(self, serializer):
        created_user = serializer.save()

        record_audit_event(
            actor=self.request.user,
            category="USER",
            action="USER_CREATED",
            target_type="User",
            target_id=created_user.pk,
            description=f"Created user account {created_user.email}.",
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = self.get_object()

        before = {
            "email": instance.email,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "username": instance.username,
        }

        updated_user = serializer.save()

        after = {
            "email": updated_user.email,
            "first_name": updated_user.first_name,
            "last_name": updated_user.last_name,
            "username": updated_user.username,
        }

        changes = {
            key: {
                "before": before[key],
                "after": after[key],
            }
            for key in before
            if before[key] != after[key]
        }

        if changes:
            record_audit_event(
                actor=self.request.user,
                category="USER",
                action="USER_UPDATED",
                target_type="User",
                target_id=updated_user.pk,
                description=f"Updated user account {updated_user.email}.",
                changes=changes,
                request=self.request,
            )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def deactivate(self, request, pk=None):
        target_user = self.get_object()

        if target_user.pk == request.user.pk:
            raise PermissionDenied(
                "You cannot deactivate your own account."
            )

        if target_user.is_superuser:
            raise PermissionDenied(
                "A superuser account cannot be deactivated through this endpoint."
            )

        if not target_user.is_active:
            return Response(
                {"detail": "User is already inactive."},
                status=status.HTTP_200_OK,
            )

        target_user.is_active = False
        target_user.save(update_fields=["is_active"])

        from apps.accounts.models import UserRole

        UserRole.objects.filter(
            user=target_user,
            is_active=True,
        ).update(is_active=False)

        record_audit_event(
            actor=request.user,
            category="USER",
            action="USER_DEACTIVATED",
            target_type="User",
            target_id=target_user.pk,
            description=f"Deactivated user {target_user.email}.",
            request=request,
        )

        return Response({
            "detail": "User deactivated successfully."
        })

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def activate(self, request, pk=None):
        target_user = self.get_object()

        if target_user.is_active:
            return Response({
                "detail": "User is already active."
            })

        target_user.is_active = True
        target_user.save(update_fields=["is_active"])

        # Previous assignments remain inactive. Reactivation must
        # require an explicit new role assignment.
        record_audit_event(
            actor=request.user,
            category="USER",
            action="USER_ACTIVATED",
            target_type="User",
            target_id=target_user.pk,
            description=f"Reactivated user {target_user.email}.",
            request=request,
        )

        return Response({
            "detail": "User activated. Assign roles explicitly."
        })
