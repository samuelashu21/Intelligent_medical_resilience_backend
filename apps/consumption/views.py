from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission

from apps.consumption.models import (
    ConsumptionAnomaly,
    ConsumptionRecordStatus,
    DailyConsumption,
    MonthlyConsumptionReport,
)

from apps.consumption.serializers import (
    ConsumptionAnomalySerializer,
    DailyConsumptionSerializer,
    MonthlyConsumptionReportSerializer,
)

from apps.consumption.services import (
    approve_monthly_report,
    detect_consumption_anomalies,
    generate_monthly_report,
    record_consumption,
    reject_monthly_report,
    submit_monthly_report,
)


def check_facility_permission(user, permission_code, facility):
    if user.is_superuser:
        return True

    return user_has_permission(
        user,
        permission_code,
        organization=facility.organization,
    )


class DailyConsumptionViewSet(viewsets.ModelViewSet):
    serializer_class = DailyConsumptionSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        from apps.inventory.permissions import HasInventoryPermission

        self.required_permissions = (
            ["consumption.create"]
            if self.action in ["create", "partial_update"]
            else ["consumption.view"]
        )

        return [HasInventoryPermission()]

    def get_queryset(self):
        queryset = DailyConsumption.objects.select_related(
            "facility",
            "facility__organization",
            "medicine",
            "batch",
            "recorded_by",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="consumption.view",
        )

        return queryset.filter(
            facility__organization_id__in=organization_ids
        )

    def perform_create(self, serializer):
        facility = serializer.validated_data["facility"]

        if not check_facility_permission(
            self.request.user,
            "consumption.create",
            facility,
        ):
            raise ValidationError(
                "You cannot record consumption for this facility."
            )

        data = serializer.validated_data

        record = record_consumption(
            facility=data["facility"],
            medicine=data["medicine"],
            consumption_date=data["consumption_date"],
            quantity=data["quantity"],
            unit_code=data["unit_code"],
            recorded_by=self.request.user,
            batch=data.get("batch"),
            source=data.get("source", "DISPENSING"),
            reference_number=data.get("reference_number", ""),
            notes=data.get("notes", ""),
        )

        serializer.instance = record

    def perform_update(self, serializer):
        record = self.get_object()

        if record.recorded_by_id != self.request.user.pk:
            raise ValidationError(
                "Only the original recorder can edit this record."
            )

        if not check_facility_permission(
            self.request.user,
            "consumption.create",
            record.facility,
        ):
            raise ValidationError(
                "You cannot edit consumption for this facility."
            )

        serializer.save()


class MonthlyConsumptionReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MonthlyConsumptionReportSerializer

    def get_permissions(self):
        from apps.inventory.permissions import HasInventoryPermission

        permissions = {
            "list": ["consumption.view"],
            "retrieve": ["consumption.view"],
            "generate": ["consumption.create"],
            "submit": ["consumption.submit"],
            "approve": ["consumption.approve"],
            "reject": ["consumption.approve"],
        }

        self.required_permissions = permissions.get(
            self.action,
            ["consumption.view"],
        )

        return [HasInventoryPermission()]

    def get_queryset(self):
        queryset = MonthlyConsumptionReport.objects.select_related(
            "facility",
            "facility__organization",
            "medicine",
            "submitted_by",
            "approved_by",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="consumption.view",
        )

        return queryset.filter(
            facility__organization_id__in=organization_ids
        )

    @action(detail=False, methods=["post"])
    def generate(self, request):
        from apps.facilities.models import Facility
        from apps.medicines.models import Medicine

        facility = Facility.objects.filter(
            pk=request.data.get("facility")
        ).first()

        medicine = Medicine.objects.filter(
            pk=request.data.get("medicine")
        ).first()

        if not facility or not medicine:
            raise ValidationError(
                "A valid facility and medicine are required."
            )

        if not check_facility_permission(
            request.user,
            "consumption.create",
            facility,
        ):
            raise ValidationError(
                "You cannot generate reports for this facility."
            )

        required_fields = [
            "year",
            "month",
            "opening_balance",
            "received_quantity",
            "losses_quantity",
            "closing_balance",
            "reporting_unit",
        ]

        missing = [
            field for field in required_fields
            if field not in request.data
        ]

        if missing:
            raise ValidationError({
                "missing_fields": missing,
            })

        try:
            report = generate_monthly_report(
                facility=facility,
                medicine=medicine,
                year=int(request.data["year"]),
                month=int(request.data["month"]),
                opening_balance=request.data["opening_balance"],
                received_quantity=request.data["received_quantity"],
                losses_quantity=request.data["losses_quantity"],
                closing_balance=request.data["closing_balance"],
                reporting_unit=request.data["reporting_unit"],
                stockout_days=int(request.data.get("stockout_days", 0)),
                notes=request.data.get("notes", ""),
            )
        except (DjangoValidationError, ValueError) as exc:
            raise ValidationError(
                getattr(exc, "messages", [str(exc)])
            )

        return Response(
            self.get_serializer(report).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        report = self.get_object()

        if not check_facility_permission(
            request.user,
            "consumption.submit",
            report.facility,
        ):
            raise ValidationError(
                "You cannot submit this report."
            )

        try:
            report = submit_monthly_report(
                report.pk,
                submitted_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        report = self.get_object()

        if not check_facility_permission(
            request.user,
            "consumption.approve",
            report.facility,
        ):
            raise ValidationError(
                "You cannot approve this report."
            )

        try:
            report = approve_monthly_report(
                report.pk,
                approved_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        report = self.get_object()

        if not check_facility_permission(
            request.user,
            "consumption.approve",
            report.facility,
        ):
            raise ValidationError(
                "You cannot reject this report."
            )

        try:
            report = reject_monthly_report(
                report.pk,
                rejected_by=request.user,
                reason=request.data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(report).data)


class ConsumptionAnomalyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsumptionAnomalySerializer

    def get_permissions(self):
        from apps.inventory.permissions import HasInventoryPermission

        self.required_permissions = ["consumption.view"]
        return [HasInventoryPermission()]

    def get_queryset(self):
        queryset = ConsumptionAnomaly.objects.select_related(
            "facility",
            "facility__organization",
            "medicine",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="consumption.view",
        )

        return queryset.filter(
            facility__organization_id__in=organization_ids
        )