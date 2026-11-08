from rest_framework.permissions import BasePermission

from apps.accounts.services import user_has_permission


class HasSupplierPermission(BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        if request.user.is_superuser:
            return True

        required = getattr(
            view,
            "required_permissions",
            None,
        )

        if not required:
            return False

        return all(
            user_has_permission(
                request.user,
                permission_code,
            )
            for permission_code in required
        )