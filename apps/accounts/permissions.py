from rest_framework.permissions import BasePermission

from apps.accounts.services import (
    get_user_permissions,
    user_has_permission,
)


class HasSystemPermission(BasePermission):
    """
    Permission class that checks system-level required permissions.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        if user.is_superuser:
            return True

        required_permissions = getattr(
            view,
            "required_permissions",
            (),
        )

        if not required_permissions:
            return False

        granted_permissions = get_user_permissions(user)

        # All declared permissions must be granted.
        return set(required_permissions).issubset(granted_permissions)


class HasScopedPermission(BasePermission):
    """
    Permission class that checks required permissions
    against an organization or facility scope.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        required_permissions = getattr(
            view,
            "required_permissions",
            [],
        )

        if not required_permissions:
            return False

        scope = view.get_permission_scope(request) or {}

        organization = scope.get("organization")
        facility = scope.get("facility")

        return all(
            user_has_permission(
                user,
                permission_code,
                organization=organization,
                facility=facility,
            )
            for permission_code in required_permissions
        )
