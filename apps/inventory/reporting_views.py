 
import csv

from django.http import HttpResponse

from rest_framework.exceptions import (
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)
from apps.accounts.services import user_has_permission

from apps.facilities.models import Facility

from apps.inventory.reporting_services import (
    get_expiry_report,
    get_facility_stock_summary,
    get_high_coverage_report,
    get_low_stock_report,
    get_medicine_stock_status,
    get_stock_dashboard_summary,
    get_stockout_report,
)

from apps.inventory.reporting_serializers import (
    ExpiryReportSerializer,
    StockDashboardSummarySerializer,
    StockStatusSerializer,
)


class BaseStockReportView(APIView):
    permission_classes = []

    required_permission = "inventory.view"

    def get_scope(self, request):
        if not request.user.is_authenticated:
            raise NotAuthenticated()

        if request.user.is_superuser:
            return None

        organization_ids = get_user_accessible_organization_ids(
            request.user,
            permission_code=self.required_permission,
        )

        if not organization_ids:
            return []

        return organization_ids

    def get_facility_filter(self, request, organization_ids):
        facility_id = request.query_params.get("facility")

        if not facility_id:
            return None

        facility = Facility.objects.filter(
            pk=facility_id
        ).first()

        if not facility:
            raise ValidationError({
                "facility": "Facility not found."
            })

        if not request.user.is_superuser:
            allowed = user_has_permission(
                request.user,
                self.required_permission,
                organization=facility.organization,
            )

            if not allowed:
                raise PermissionDenied(
                    "You cannot access reports for this facility."
                )

        return str(facility.pk)


class StockDashboardView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        result = get_stock_dashboard_summary(
            organization_ids=organization_ids,
            facility_id=facility_id,
        )

        return Response(
            StockDashboardSummarySerializer(result).data
        )


class StockStatusReportView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        medicine_id = request.query_params.get("medicine")

        rows = get_medicine_stock_status(
            organization_ids=organization_ids,
            facility_id=facility_id,
            medicine_id=medicine_id,
        )

        status_filter = request.query_params.get("status")

        if status_filter:
            valid_statuses = {
                "STOCKOUT",
                "CRITICAL",
                "LOW",
                "ADEQUATE",
                "HIGH_COVERAGE",
                "NO_CONSUMPTION_HISTORY",
            }

            if status_filter not in valid_statuses:
                raise ValidationError({
                    "status": "Unsupported stock status."
                })

            rows = [
                row for row in rows
                if row["status"] == status_filter
            ]

        return Response(
            StockStatusSerializer(rows, many=True).data
        )


class StockoutReportView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        rows = get_stockout_report(
            organization_ids=organization_ids,
            facility_id=facility_id,
        )

        return Response(
            StockStatusSerializer(rows, many=True).data
        )


class LowStockReportView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        rows = get_low_stock_report(
            organization_ids=organization_ids,
            facility_id=facility_id,
        )

        return Response(
            StockStatusSerializer(rows, many=True).data
        )


class HighCoverageReportView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        rows = get_high_coverage_report(
            organization_ids=organization_ids,
            facility_id=facility_id,
        )

        return Response(
            StockStatusSerializer(rows, many=True).data
        )


class ExpiryReportView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        try:
            days = int(
                request.query_params.get("days", 90)
            )
        except (TypeError, ValueError):
            raise ValidationError({
                "days": "Days must be an integer."
            })

        rows = get_expiry_report(
            organization_ids=organization_ids,
            facility_id=facility_id,
            days=days,
        )

        return Response(
            ExpiryReportSerializer(rows, many=True).data
        )


class FacilityStockSummaryView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = request.query_params.get("facility")

        if not facility_id:
            raise ValidationError({
                "facility": "Facility ID is required."
            })

        self.get_facility_filter(
            request,
            organization_ids,
        )

        result = get_facility_stock_summary(
            facility_id=facility_id,
            organization_ids=organization_ids,
        )

        return Response(result)


class StockStatusCSVExportView(BaseStockReportView):

    def get(self, request, *args, **kwargs):
        organization_ids = self.get_scope(request)

        facility_id = self.get_facility_filter(
            request,
            organization_ids,
        )

        rows = get_medicine_stock_status(
            organization_ids=organization_ids,
            facility_id=facility_id,
        )

        response = HttpResponse(
            content_type="text/csv"
        )

        response["Content-Disposition"] = (
            'attachment; filename="stock-status-report.csv"'
        )

        fieldnames = [
            "facility_code",
            "facility_name",
            "medicine_code",
            "medicine_name",
            "on_hand",
            "reserved",
            "available",
            "amc",
            "months_of_stock",
            "status",
        ]

        writer = csv.DictWriter(
            response,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow({
                field: row.get(field, "")
                for field in fieldnames
            })

        return response
 