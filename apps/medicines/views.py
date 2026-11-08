from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import HasSystemPermission
from apps.medicines.models import (
    AdministrationRoute,
    DosageForm,
    MeasurementUnit,
    Medicine,
    TherapeuticCategory,
)

from apps.medicines.serializers import (
    AdministrationRouteSerializer,
    DosageFormSerializer,
    MeasurementUnitSerializer,
    MedicineSerializer,
    TherapeuticCategorySerializer,
)

from apps.medicines.services import search_medicines
from apps.audit.services import record_audit_event


class MedicineViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineSerializer

    permission_classes = [
        HasSystemPermission,
    ]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["medicines.create"]

        elif self.action in [
            "update",
            "partial_update",
            "destroy",
            "deactivate",
            "activate",
        ]:
            self.required_permissions = ["medicines.update"]

        else:
            self.required_permissions = ["medicines.view"]

        return super().get_permissions()

    def get_queryset(self):
        return Medicine.objects.select_related(
            "therapeutic_category",
            "dosage_form",
            "administration_route",
            "strength_unit",
            "dispensing_unit",
        ).all()

    def filter_queryset(self, queryset):
        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        dosage_form = self.request.query_params.get("dosage_form")
        atc_code = self.request.query_params.get("atc_code")
        essential_param = self.request.query_params.get("essential")
        active_param = self.request.query_params.get("active")

        essential = None
        if essential_param is not None:
            if essential_param.lower() not in ["true", "false"]:
                raise ValidationError({
                    "essential": "Use true or false."
                })
            essential = essential_param.lower() == "true"

        active = True
        if active_param is not None:
            if active_param.lower() not in ["true", "false"]:
                raise ValidationError({
                    "active": "Use true or false."
                })
            active = active_param.lower() == "true"

        return search_medicines(
            search=search,
            category=category,
            dosage_form=dosage_form,
            atc_code=atc_code,
            essential=essential,
            active=active,
        )

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                medicine = serializer.save()

                record_audit_event(
                    actor=self.request.user,
                    category="SYSTEM",
                    action="MEDICINE_CREATED",
                    target_type="Medicine",
                    target_id=medicine.pk,
                    description=(
                        f"Created medicine catalog entry "
                        f"{medicine.generic_name}."
                    ),
                    request=self.request,
                )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "message_dict", {"detail": exc.messages})
            )

        except IntegrityError:
            raise ValidationError({
                "detail": "A medicine with this code already exists."
            })

    def perform_update(self, serializer):
        instance = self.get_object()

        before = {
            "generic_name": instance.generic_name,
            "brand_name": instance.brand_name,
            "strength_display": instance.strength_display,
            "is_essential": instance.is_essential,
            "is_active": instance.is_active,
        }

        try:
            with transaction.atomic():
                medicine = serializer.save()

                after = {
                    "generic_name": medicine.generic_name,
                    "brand_name": medicine.brand_name,
                    "strength_display": medicine.strength_display,
                    "is_essential": medicine.is_essential,
                    "is_active": medicine.is_active,
                }

                changes = {
                    key: {
                        "before": before[key],
                        "after": after[key],
                    }
                    for key in before
                    if before[key] != after[key]
                }

                if changes:
                    record_audit_event(
                        actor=self.request.user,
                        category="SYSTEM",
                        action="MEDICINE_UPDATED",
                        target_type="Medicine",
                        target_id=medicine.pk,
                        description=(
                            f"Updated medicine {medicine.generic_name}."
                        ),
                        changes=changes,
                        request=self.request,
                    )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "message_dict", {"detail": exc.messages})
            )

        except IntegrityError:
            raise ValidationError({
                "detail": "The update conflicts with an existing record."
            })

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    "Medicine deletion is disabled. "
                    "Use the deactivate endpoint instead."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        medicine = self.get_object()

        if not medicine.is_active:
            return Response({
                "detail": "Medicine is already inactive."
            })

        medicine.is_active = False
        medicine.save(update_fields=["is_active", "updated_at"])

        record_audit_event(
            actor=request.user,
            category="SYSTEM",
            action="MEDICINE_DEACTIVATED",
            target_type="Medicine",
            target_id=medicine.pk,
            description=f"Deactivated {medicine.generic_name}.",
            request=request,
        )

        return Response({
            "detail": "Medicine deactivated successfully."
        })

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        medicine = self.get_object()

        if medicine.is_active:
            return Response({
                "detail": "Medicine is already active."
            })

        medicine.is_active = True
        medicine.save(update_fields=["is_active", "updated_at"])

        record_audit_event(
            actor=request.user,
            category="SYSTEM",
            action="MEDICINE_ACTIVATED",
            target_type="Medicine",
            target_id=medicine.pk,
            description=f"Activated {medicine.generic_name}.",
            request=request,
        )

        return Response({
            "detail": "Medicine activated successfully."
        })


class TherapeuticCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TherapeuticCategory.objects.filter(is_active=True)
    serializer_class = TherapeuticCategorySerializer
    permission_classes = [HasSystemPermission]
    required_permissions = ["medicines.view"]


class DosageFormViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DosageForm.objects.filter(is_active=True)
    serializer_class = DosageFormSerializer
    permission_classes = [HasSystemPermission]
    required_permissions = ["medicines.view"]


class AdministrationRouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdministrationRoute.objects.filter(is_active=True)
    serializer_class = AdministrationRouteSerializer
    permission_classes = [HasSystemPermission]
    required_permissions = ["medicines.view"]


class MeasurementUnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MeasurementUnit.objects.filter(is_active=True)
    serializer_class = MeasurementUnitSerializer
    permission_classes = [HasSystemPermission]
    required_permissions = ["medicines.view"]