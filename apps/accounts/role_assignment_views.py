
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import UserRole
from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_active_role_assignments,
    get_user_accessible_facility_ids,
    get_user_accessible_organization_ids,
)
from apps.accounts.serializers import UserRoleAssignmentSerializer
from apps.accounts.services import assign_role
from apps.accounts.services import revoke_role_assignment
from apps.accounts.services import user_has_permission
from apps.audit.services import record_audit_event


class UserRoleAssignmentViewSet(viewsets.ModelViewSet):
    """
    Manage scoped user-role assignments.

    Revocation is a soft operation: the assignment is deactivated,
    not deleted.
    """

    serializer_class = UserRoleAssignmentSerializer

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    permission_classes = [
        HasSystemPermission,
    ]

    def get_permissions(self):
        if self.action in ["create", "revoke"]:
            self.required_permissions = ["users.assign_roles"]

        elif self.action in ["partial_update"]:
            self.required_permissions = ["users.assign_roles"]

        else:
            self.required_permissions = ["users.view"]

        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user

        assignments = get_active_role_assignments(user)

        if user.is_superuser:
            return UserRole.objects.select_related(
                "user",
                "role",
                "organization",
                "facility",
                "assigned_by",
            )

        global_access = assignments.filter(
            organization__isnull=True,
            facility__isnull=True,
        ).exists()

        queryset = UserRole.objects.select_related(
            "user",
            "role",
            "organization",
            "facility",
            "assigned_by",
        )

        if global_access:
            return queryset

        organization_ids = get_user_accessible_organization_ids(user)
        facility_ids = get_user_accessible_facility_ids(user)

        return queryset.filter(
            Q(organization_id__in=organization_ids)
            | Q(facility_id__in=facility_ids)
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = serializer.validated_data["user"]
        role = serializer.validated_data["role"]
        organization = serializer.validated_data.get("organization")
        facility = serializer.validated_data.get("facility")
        valid_from = serializer.validated_data.get("valid_from")
        valid_until = serializer.validated_data.get("valid_until")

        # Scope-specific authorization.
        if organization is None and facility is None:
            if not request.user.is_superuser:
                raise PermissionDenied(
                    "Only a superuser can create a global role assignment."
                )

        elif facility is not None:
            if not user_has_permission(
                request.user,
                "users.assign_roles",
                facility=facility,
            ):
                raise PermissionDenied(
                    "You cannot assign roles at this facility."
                )

        elif organization is not None:
            if not user_has_permission(
                request.user,
                "users.assign_roles",
                organization=organization,
            ):
                raise PermissionDenied(
                    "You cannot assign roles within this organization."
                )

        with transaction.atomic():
            assignment = assign_role(
                user=target_user,
                role=role,
                assigned_by=request.user,
                organization=organization,
                facility=facility,
                valid_from=valid_from,
                valid_until=valid_until,
            )

            record_audit_event(
                actor=request.user,
                category="ROLE",
                action="ROLE_ASSIGNED",
                target_type="UserRole",
                target_id=assignment.pk,
                description=(
                    f"Assigned {role.code} to {target_user.email}."
                ),
                organization=organization,
                facility=facility,
                changes={
                    "role": role.code,
                    "is_active": True,
                    "valid_from": (
                        valid_from.isoformat() if valid_from else None
                    ),
                    "valid_until": (
                        valid_until.isoformat() if valid_until else None
                    ),
                },
                request=request,
            )

        output = self.get_serializer(assignment)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Only validity dates can be changed through PATCH.
        Role, user, and scope are immutable after assignment.
        """

        assignment = self.get_object()

        allowed_fields = {
            "valid_from",
            "valid_until",
        }

        unexpected = set(request.data.keys()) - allowed_fields

        if unexpected:
            return Response(
                {
                    "detail": (
                        "Only valid_from and valid_until can be changed. "
                        "Create a new assignment to change role or scope."
                    ),
                    "unsupported_fields": sorted(unexpected),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            assignment,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        before = {
            "valid_from": (
                assignment.valid_from.isoformat()
                if assignment.valid_from else None
            ),
            "valid_until": (
                assignment.valid_until.isoformat()
                if assignment.valid_until else None
            ),
        }

        updated = serializer.save()

        after = {
            "valid_from": (
                updated.valid_from.isoformat()
                if updated.valid_from else None
            ),
            "valid_until": (
                updated.valid_until.isoformat()
                if updated.valid_until else None
            ),
        }

        record_audit_event(
            actor=request.user,
            category="ROLE",
            action="ROLE_VALIDITY_UPDATED",
            target_type="UserRole",
            target_id=updated.pk,
            description="Updated role assignment validity.",
            organization=updated.organization,
            facility=updated.facility,
            changes={
                key: {
                    "before": before[key],
                    "after": after[key],
                }
                for key in before
                if before[key] != after[key]
            },
            request=request,
        )

        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def revoke(self, request, pk=None):
        assignment = self.get_object()

        if not assignment.is_active:
            return Response({
                "detail": "Role assignment is already inactive."
            })

        if assignment.user_id == request.user.pk:
            raise PermissionDenied(
                "You cannot revoke your own role assignment."
            )

        # Scope-specific authorization.
        if assignment.facility_id:
            allowed = user_has_permission(
                request.user,
                "users.assign_roles",
                facility=assignment.facility,
            )

        elif assignment.organization_id:
            allowed = user_has_permission(
                request.user,
                "users.assign_roles",
                organization=assignment.organization,
            )

        else:
            allowed = request.user.is_superuser

        if not allowed:
            raise PermissionDenied(
                "You cannot revoke this role assignment."
            )

        assignment = revoke_role_assignment(assignment)

        record_audit_event(
            actor=request.user,
            category="ROLE",
            action="ROLE_REVOKED",
            target_type="UserRole",
            target_id=assignment.pk,
            description=(
                f"Revoked {assignment.role.code} from "
                f"{assignment.user.email}."
            ),
            organization=assignment.organization,
            facility=assignment.facility,
            changes={
                "is_active": {
                    "before": True,
                    "after": False,
                }
            },
            request=request,
        )

        return Response({
            "detail": "Role assignment revoked successfully."
        })
