
from rest_framework.permissions import BasePermission

from apps.accounts.services import (
    get_user_permissions,
)


class HasSystemPermission(BasePermission):

    message = (
        "You do not have permission to perform this action."
    )

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
        return set(required_permissions).issubset(
            granted_permissions
        )
