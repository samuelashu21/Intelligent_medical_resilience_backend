from rest_framework.permissions import BasePermission


class MedicineCatalogPermission(BasePermission):
    """
    Medicine catalog authorization.

    Read operations require medicines.view.
    Create operations require medicines.create.
    Update operations require medicines.update.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        if user.is_superuser:
            return True

        required_permission = getattr(
            view,
            "required_permissions",
            None,
        )

        if not required_permission:
            return False

        from apps.accounts.services import user_has_permission

        return all(
            user_has_permission(user, code)
            for code in required_permission
        )