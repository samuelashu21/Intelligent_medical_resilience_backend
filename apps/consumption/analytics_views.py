from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)

from apps.accounts.services import user_has_permission

from apps.facilities.models import Facility
from apps.medicines.models import Medicine

from apps.consumption.services import (
    calculate_average_monthly_consumption,
    detect_consumption_anomalies,
)


class AverageMonthlyConsumptionView(APIView):
    permission_classes = []

    def get(self, request):
        if not request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated

            raise NotAuthenticated()

        facility_id = request.query_params.get("facility")
        medicine_id = request.query_params.get("medicine")

        if not facility_id or not medicine_id:
            raise ValidationError("Both facility and medicine are required.")

        facility = Facility.objects.filter(pk=facility_id).first()
        medicine = Medicine.objects.filter(pk=medicine_id).first()

        if not facility or not medicine:
            raise ValidationError("Facility or medicine not found.")

        if not user_has_permission(
            request.user,
            "consumption.view",
            organization=facility.organization,
        ):
            raise ValidationError("You cannot view consumption for this facility.")

        months = int(request.query_params.get("months", 3))

        if not 1 <= months <= 24:
            raise ValidationError("Months must be between 1 and 24.")

        result = calculate_average_monthly_consumption(
            facility_id=facility.pk,
            medicine_id=medicine.pk,
            number_of_months=months,
        )

        return Response(
            {
                "facility": str(facility.pk),
                "facility_name": facility.name,
                "medicine": str(medicine.pk),
                "medicine_name": medicine.generic_name,
                "period_months": result["months_included"],
                "total_consumption": str(result["total_consumption"]),
                "average_monthly_consumption": str(
                    result["average_monthly_consumption"]
                ),
            }
        )


class DetectConsumptionAnomaliesView(APIView):
    permission_classes = []

    def post(self, request):
        if not request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated

            raise NotAuthenticated()

        facility = Facility.objects.filter(pk=request.data.get("facility")).first()

        medicine = Medicine.objects.filter(pk=request.data.get("medicine")).first()

        if not facility or not medicine:
            raise ValidationError("A valid facility and medicine are required.")

        if not user_has_permission(
            request.user,
            "consumption.create",
            organization=facility.organization,
        ):
            raise ValidationError("You cannot run anomaly detection for this facility.")

        try:
            year = int(request.data["year"])
            month = int(request.data["month"])
        except (KeyError, ValueError):
            raise ValidationError("A valid year and month are required.")

        anomalies = detect_consumption_anomalies(
            facility=facility,
            medicine=medicine,
            year=year,
            month=month,
        )

        return Response(
            {
                "facility": str(facility.pk),
                "medicine": str(medicine.pk),
                "anomalies_detected": len(anomalies),
                "anomaly_ids": [str(anomaly.pk) for anomaly in anomalies],
            }
        )
