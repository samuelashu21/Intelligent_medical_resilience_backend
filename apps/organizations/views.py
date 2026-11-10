from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.services import user_has_permission
from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
    user_can_access_organization,
)

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

from apps.organizations.serializers import (
    OrganizationSerializer,
    OrganizationUnitTypeSerializer,
)


class OrganizationUnitTypeViewSet(viewsets.ModelViewSet):

    queryset = OrganizationUnitType.objects.all()
    serializer_class = OrganizationUnitTypeSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    required_permissions = ["organizations.view"]

    def get_permissions(self):
        if self.action in ["create"]:
            self.required_permissions = ["organizations.create"]

        elif self.action in ["update", "partial_update"]:
            self.required_permissions = ["organizations.update"]

        elif self.action == "destroy":
            self.required_permissions = ["organizations.update"]

        else:
            self.required_permissions = ["organizations.view"]

        return super().get_permissions()


class OrganizationViewSet(viewsets.ModelViewSet):

    serializer_class = OrganizationSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_queryset(self):
        user = self.request.user

        permission_code = (
            "organizations.update"
            if self.action in ["update", "partial_update", "destroy"]
            else "organizations.view"
        )

        accessible_ids = get_user_accessible_organization_ids(
            user,
            permission_code=permission_code,
        )

        queryset = Organization.objects.select_related(
            "organization_type",
            "parent",
        ).filter(
            id__in=accessible_ids,
        )

        organization_type = self.request.query_params.get("organization_type")

        if organization_type:
            queryset = queryset.filter(organization_type__code=organization_type)

        parent_id = self.request.query_params.get("parent")

        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)

        return queryset

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["organizations.create"]

        elif self.action in ["update", "partial_update", "destroy"]:
            self.required_permissions = ["organizations.update"]

        else:
            self.required_permissions = ["organizations.view"]

        return super().get_permissions()

    def perform_create(self, serializer):
        parent = serializer.validated_data.get("parent")

        if parent and not user_has_permission(
            self.request.user,
            "organizations.create",
            organization=parent,
        ):
            raise PermissionDenied(
                "You cannot create an organization under this parent."
            )

        if not parent and not self.request.user.is_superuser:
            # Creating a root organization is a global administrative action.
            from apps.accounts.scope_services import get_active_role_assignments

            has_global_assignment = (
                get_active_role_assignments(self.request.user)
                .filter(
                    organization__isnull=True,
                    facility__isnull=True,
                )
                .exists()
            )

            if not has_global_assignment:
                raise PermissionDenied(
                    "Only globally scoped administrators can create root organizations."
                )

        serializer.save()

    def perform_update(self, serializer):
        new_parent = serializer.validated_data.get(
            "parent",
            serializer.instance.parent,
        )

        if new_parent and not user_has_permission(
            self.request.user,
            "organizations.update",
            organization=new_parent,
        ):
            raise PermissionDenied(
                "You cannot move this organization under the selected parent."
            )

        serializer.save()
