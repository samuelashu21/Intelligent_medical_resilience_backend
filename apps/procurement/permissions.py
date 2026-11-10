from rest_framework.permissions import BasePermission

from apps.accounts.services import user_has_permission


class HasProcurementPermission(BasePermission):

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        if user.is_superuser:
            return True

        required = getattr(
            view,
            "required_permissions",
            [],
        )

        if not required:
            return False

        return all(user_has_permission(user, permission) for permission in required)
