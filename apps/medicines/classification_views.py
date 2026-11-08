from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasSystemPermission

from apps.medicines.models import (
    ATCClassification,
    Country,
    EssentialMedicineItem,
    EssentialMedicineList,
    MedicineEligibilityRule,
    MedicineNationalCode,
    MedicinePresentation,
)

from apps.medicines.classification_serializers import (
    ATCClassificationSerializer,
    CountrySerializer,
    EssentialMedicineItemSerializer,
    EssentialMedicineListSerializer,
    MedicineEligibilityRuleSerializer,
    MedicineNationalCodeSerializer,
    MedicinePresentationSerializer,
)

from apps.medicines.classification_services import (
    get_current_essential_medicines,
    get_medicines_by_atc,
)


class CatalogPermissionMixin:
    permission_classes = [HasSystemPermission]

    def get_permissions(self):
        if self.action in ["create"]:
            self.required_permissions = ["medicines.create"]

        elif self.action in [
            "update",
            "partial_update",
            "destroy",
        ]:
            self.required_permissions = ["medicines.update"]

        else:
            self.required_permissions = ["medicines.view"]

        return super().get_permissions()


class CountryViewSet(CatalogPermissionMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer


class ATCClassificationViewSet(
    CatalogPermissionMixin,
    viewsets.ModelViewSet,
):
    serializer_class = ATCClassificationSerializer

    def get_queryset(self):
        queryset = ATCClassification.objects.select_related(
            "parent"
        ).all()

        level = self.request.query_params.get("level")
        search = self.request.query_params.get("search")
        parent_code = self.request.query_params.get("parent_code")

        if level:
            if level not in {"1", "2", "3", "4", "5"}:
                raise ValidationError({
                    "level": "Level must be between 1 and 5."
                })
            queryset = queryset.filter(level=int(level))

        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
            )

        if parent_code:
            queryset = queryset.filter(parent__code=parent_code)

        return queryset

    @action(detail=True, methods=["get"])
    def medicines(self, request, pk=None):
        classification = self.get_object()

        medicines = get_medicines_by_atc(classification)

        from apps.medicines.serializers import MedicineSerializer

        page = self.paginate_queryset(medicines)

        if page is not None:
            serializer = MedicineSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MedicineSerializer(medicines, many=True)
        return Response(serializer.data)


class EssentialMedicineListViewSet(
    CatalogPermissionMixin,
    viewsets.ModelViewSet,
):
    queryset = EssentialMedicineList.objects.select_related(
        "country"
    ).all()

    serializer_class = EssentialMedicineListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        country = self.request.query_params.get("country")
        if country:
            queryset = queryset.filter(country__code=country.upper())

        return queryset


class EssentialMedicineItemViewSet(
    CatalogPermissionMixin,
    viewsets.ModelViewSet,
):
    queryset = EssentialMedicineItem.objects.select_related(
        "medicine",
        "essential_list",
        "essential_list__country",
    ).all()

    serializer_class = EssentialMedicineItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        list_id = self.request.query_params.get("essential_list")
        if list_id:
            queryset = queryset.filter(essential_list_id=list_id)

        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)

        return queryset


class MedicineNationalCodeViewSet(
    CatalogPermissionMixin,
    viewsets.ModelViewSet,
):
    queryset = MedicineNationalCode.objects.select_related(
        "country",
        "medicine",
    ).all()

    serializer_class = MedicineNationalCodeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        country = self.request.query_params.get("country")
        if country:
            queryset = queryset.filter(country__code=country.upper())

        return queryset


class MedicinePresentationViewSet(
    CatalogPermissionMixin,
    viewsets.ModelViewSet,
):
    queryset = MedicinePresentation.objects.select_related(
        "medicine",
        "package_unit",
    ).all()

    serializer_class = MedicinePresentationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)

        return queryset


class MedicineEligibilityRuleViewSet(
    CatalogPermissionMixin,
    viewsets.ModelViewSet,
):
    queryset = MedicineEligibilityRule.objects.select_related(
        "medicine",
        "country",
        "organization",
        "facility",
    ).all()

    serializer_class = MedicineEligibilityRuleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)

        return queryset


class CurrentEssentialMedicinesViewSet(
    CatalogPermissionMixin,
    viewsets.GenericViewSet,
):
    def list(self, request):
        country_code = request.query_params.get("country")

        if not country_code:
            raise ValidationError({
                "country": "Country ISO code is required."
            })

        country = Country.objects.filter(
            code=country_code.upper(),
            is_active=True,
        ).first()

        if not country:
            raise ValidationError({
                "country": "Country was not found."
            })

        medicines = get_current_essential_medicines(country)

        from apps.medicines.serializers import MedicineSerializer

        page = self.paginate_queryset(medicines)

        if page is not None:
            serializer = MedicineSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(
            MedicineSerializer(medicines, many=True).data
        )