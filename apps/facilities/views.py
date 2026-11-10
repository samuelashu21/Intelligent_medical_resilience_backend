from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.services import user_has_permission
from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
    user_can_access_organization,
)

from apps.facilities.models import Facility, FacilityType
from apps.facilities.serializers import (
    FacilitySerializer,
    FacilityTypeSerializer,
)


class FacilityTypeViewSet(viewsets.ModelViewSet):

    queryset = FacilityType.objects.all()
    serializer_class = FacilityTypeSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["facilities.create"]

        elif self.action in ["update", "partial_update", "destroy"]:
            self.required_permissions = ["facilities.update"]

        else:
            self.required_permissions = ["facilities.view"]

        return super().get_permissions()


class FacilityViewSet(viewsets.ModelViewSet):

    serializer_class = FacilitySerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    def get_queryset(self):
        user = self.request.user

        permission_code = (
            "facilities.update"
            if self.action in ["update", "partial_update", "destroy"]
            else "facilities.view"
        )

        accessible_ids = get_user_accessible_facility_ids(
            user,
            permission_code=permission_code,
        )

        queryset = Facility.objects.select_related(
            "organization",
            "facility_type",
        ).filter(
            id__in=accessible_ids,
        )

        organization_id = self.request.query_params.get("organization")

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        facility_type = self.request.query_params.get("facility_type")

        if facility_type:
            queryset = queryset.filter(facility_type__code=facility_type)

        return queryset

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["facilities.create"]

        elif self.action in ["update", "partial_update", "destroy"]:
            self.required_permissions = ["facilities.update"]

        else:
            self.required_permissions = ["facilities.view"]

        return super().get_permissions()

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]

        if organization and not user_has_permission(
            self.request.user,
            "facilities.create",
            organization=organization,
        ):
            raise PermissionDenied(
                "You cannot create a facility under this organization."
            )

        serializer.save()

    def perform_update(self, serializer):
        organization = serializer.validated_data.get(
            "organization",
            serializer.instance.organization,
        )

        if organization and not user_has_permission(
            self.request.user,
            "facilities.update",
            organization=organization,
        ):
            raise PermissionDenied(
                "You cannot move this facility to the selected organization."
            )

        serializer.save()
