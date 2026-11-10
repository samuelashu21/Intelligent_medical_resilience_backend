from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from apps.inventory.visibility_services import (
    get_visible_facility_medicine_stock,
    get_facility_stock_by_medicine,
    get_visible_facility_ids,
)

from apps.inventory.visibility_classification import (
    classify_facility_medicine_stock,
)

from apps.inventory.visibility_serializers import (
    FacilityStockVisibilitySerializer,
    FacilityStockClassificationSerializer,
)

from apps.inventory.permissions import HasInventoryPermission

from apps.facilities.models import Facility
from apps.medicines.models import Medicine


class FacilityStockVisibilityView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasInventoryPermission,
    ]

    required_permissions = [
        "inventory.visibility.view",
    ]

    def get(self, request):

        medicine_id = request.query_params.get("medicine")

        if medicine_id:
            if not Medicine.objects.filter(
                pk=medicine_id
            ).exists():
                raise ValidationError({
                    "medicine": "Medicine not found."
                })

        rows = get_visible_facility_medicine_stock(
            user=request.user,
            medicine_id=medicine_id,
        )

        serializer = FacilityStockVisibilitySerializer(
            rows,
            many=True,
        )

        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        })


class MedicineFacilityAvailabilityView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasInventoryPermission,
    ]

    required_permissions = [
        "inventory.visibility.view",
    ]

    def get(self, request):

        medicine_id = request.query_params.get("medicine")

        if not medicine_id:
            raise ValidationError({
                "medicine": "Medicine ID is required."
            })

        if not Medicine.objects.filter(
            pk=medicine_id
        ).exists():
            raise ValidationError({
                "medicine": "Medicine not found."
            })

        rows = get_visible_facility_medicine_stock(
            user=request.user,
            medicine_id=medicine_id,
        )

        serializer = FacilityStockVisibilitySerializer(
            rows,
            many=True,
        )

        return Response({
            "medicine": medicine_id,
            "facility_count": len(serializer.data),
            "results": serializer.data,
        })


class FacilityStockPortfolioView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasInventoryPermission,
    ]

    required_permissions = [
        "inventory.visibility.view",
    ]

    def get(self, request, facility_id):

        visible_ids = get_visible_facility_ids(
            request.user
        )

        facility = Facility.objects.filter(
            pk=facility_id,
            is_active=True,
            id__in=visible_ids,
        ).first()

        if not facility:
            # Avoid disclosing whether an inaccessible facility exists.
            from rest_framework.exceptions import NotFound
            raise NotFound("Facility not found.")

        rows = get_facility_stock_by_medicine(
            facility_id=facility.pk
        )

        return Response({
            "facility": {
                "id": str(facility.pk),
                "code": facility.code,
                "name": facility.name,
            },
            "results": list(rows),
        })


class FacilityStockClassificationView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasInventoryPermission,
    ]

    required_permissions = [
        "inventory.visibility.view",
    ]

    def get(self, request):

        medicine_id = request.query_params.get("medicine")
        facility_id = request.query_params.get("facility")

        if not medicine_id or not facility_id:
            raise ValidationError({
                "detail": (
                    "Both medicine and facility query parameters are required."
                )
            })

        if not Medicine.objects.filter(
            pk=medicine_id
        ).exists():
            raise ValidationError({
                "medicine": "Medicine not found."
            })

        visible_ids = get_visible_facility_ids(
            request.user
        )

        if not Facility.objects.filter(
            pk=facility_id,
            id__in=visible_ids,
            is_active=True,
        ).exists():
            from rest_framework.exceptions import NotFound
            raise NotFound("Facility not found.")

        result = classify_facility_medicine_stock(
            facility_id=facility_id,
            medicine_id=medicine_id,
        )

        serializer = FacilityStockClassificationSerializer(
            result
        )

        return Response(serializer.data)