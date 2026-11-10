from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

from apps.facilities.models import (
    Facility,
    FacilityType,
)

from apps.medicines.models import (
    Medicine,
    DosageForm,
)

from apps.consumption.models import (
    ConsumptionRecordStatus,
    DailyConsumption,
)

from apps.consumption.services import (
    approve_monthly_report,
    calculate_average_monthly_consumption,
    calculate_monthly_consumption,
    generate_monthly_report,
    record_consumption,
    submit_monthly_report,
)


class ConsumptionServiceTests(TestCase):

    def setUp(self):
        # ==================================================
        # USERS
        # ==================================================

        self.user = User.objects.create_user(
            email="pharmacist@example.test",
            username="pharmacist",
            password="SecurePassword123!",
        )

        self.approver = User.objects.create_user(
            email="approver@example.test",
            username="approver",
            password="SecurePassword123!",
        )

        # ==================================================
        # ORGANIZATION TYPE
        # ==================================================

        self.organization_type = OrganizationUnitType.objects.create(
            code="CONS-ORG-TYPE",
            name="Consumption Test Organization Type",
            level=1,
        )

        # ==================================================
        # ORGANIZATION
        # ==================================================

        self.organization = Organization.objects.create(
            code="CONS-ORG",
            name="Consumption Test Organization",
            organization_type=self.organization_type,
        )

        # ==================================================
        # FACILITY TYPE
        # ==================================================

        self.facility_type = FacilityType.objects.create(
            code="HEALTH_CENTER",
            name="Health Center",
        )

        # ==================================================
        # FACILITY
        # ==================================================

        self.facility = Facility.objects.create(
            code="CONS-FAC-001",
            name="Consumption Test Facility",
            organization=self.organization,
            facility_type=self.facility_type,
        )

        # ==================================================
        # DOSAGE FORM
        # ==================================================

        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        # ==================================================
        # MEDICINE
        # ==================================================

        self.medicine = Medicine.objects.create(
            code="CONS-MED-001",
            generic_name="Test Medicine",
            dosage_form=self.dosage_form,
        )

    # ======================================================
    # DAILY CONSUMPTION
    # ======================================================

    def test_record_daily_consumption(self):
        record = record_consumption(
            facility=self.facility,
            medicine=self.medicine,
            consumption_date=date(2026, 10, 5),
            quantity=50,
            unit_code="TABLET",
            recorded_by=self.user,
        )

        self.assertEqual(
            record.quantity,
            Decimal("50"),
        )

        self.assertEqual(
            DailyConsumption.objects.count(),
            1,
        )

    # ======================================================
    # NEGATIVE CONSUMPTION VALIDATION
    # ======================================================

    def test_negative_consumption_rejected(self):
        with self.assertRaises(ValidationError):
            record_consumption(
                facility=self.facility,
                medicine=self.medicine,
                consumption_date=date(2026, 10, 5),
                quantity=-5,
                unit_code="TABLET",
                recorded_by=self.user,
            )

        self.assertEqual(
            DailyConsumption.objects.count(),
            0,
        )

    # ======================================================
    # MONTHLY CONSUMPTION CALCULATION
    # ======================================================

    def test_monthly_consumption_calculation(self):

        for day, quantity in [
            (5, 50),
            (10, 30),
            (20, 20),
        ]:
            record_consumption(
                facility=self.facility,
                medicine=self.medicine,
                consumption_date=date(2026, 10, day),
                quantity=quantity,
                unit_code="TABLET",
                recorded_by=self.user,
            )

        total = calculate_monthly_consumption(
            self.facility.pk,
            self.medicine.pk,
            2026,
            10,
        )

        self.assertEqual(
            total,
            Decimal("100"),
        )

    # ======================================================
    # AVERAGE MONTHLY CONSUMPTION
    # ======================================================

    def test_average_monthly_consumption(self):

        monthly_data = [
            (2026, 7, 90),
            (2026, 8, 120),
            (2026, 9, 150),
        ]

        for year, month, quantity in monthly_data:
            record_consumption(
                facility=self.facility,
                medicine=self.medicine,
                consumption_date=date(year, month, 15),
                quantity=quantity,
                unit_code="TABLET",
                recorded_by=self.user,
            )

        result = calculate_average_monthly_consumption(
            facility_id=self.facility.pk,
            medicine_id=self.medicine.pk,
            number_of_months=3,
            as_of=date(2026, 10, 15),
        )

        self.assertEqual(
            result["average_monthly_consumption"],
            Decimal("120"),
        )

    # ======================================================
    # MONTHLY REPORT GENERATION
    # ======================================================

    def test_monthly_report_generation(self):

        record_consumption(
            facility=self.facility,
            medicine=self.medicine,
            consumption_date=date(2026, 10, 10),
            quantity=75,
            unit_code="TABLET",
            recorded_by=self.user,
        )

        report = generate_monthly_report(
            facility=self.facility,
            medicine=self.medicine,
            year=2026,
            month=10,
            opening_balance=200,
            received_quantity=50,
            losses_quantity=5,
            closing_balance=170,
            reporting_unit="TABLET",
        )

        self.assertEqual(
            report.consumed_quantity,
            Decimal("75"),
        )

        self.assertEqual(
            report.status,
            ConsumptionRecordStatus.DRAFT,
        )

    # ======================================================
    # REPORT SUBMISSION AND APPROVAL
    # ======================================================

    def test_report_submission_and_approval(self):

        report = generate_monthly_report(
            facility=self.facility,
            medicine=self.medicine,
            year=2026,
            month=10,
            opening_balance=200,
            received_quantity=50,
            losses_quantity=5,
            closing_balance=170,
            reporting_unit="TABLET",
        )

        # Submit report
        submit_monthly_report(
            report.pk,
            submitted_by=self.user,
        )

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            ConsumptionRecordStatus.SUBMITTED,
        )

        # Approve report using a different user
        approve_monthly_report(
            report.pk,
            approved_by=self.approver,
        )

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            ConsumptionRecordStatus.APPROVED,
        )

    # ======================================================
    # SUBMITTER CANNOT APPROVE OWN REPORT
    # ======================================================

    def test_submitter_cannot_approve_own_report(self):

        report = generate_monthly_report(
            facility=self.facility,
            medicine=self.medicine,
            year=2026,
            month=10,
            opening_balance=200,
            received_quantity=50,
            losses_quantity=5,
            closing_balance=170,
            reporting_unit="TABLET",
        )

        submit_monthly_report(
            report.pk,
            submitted_by=self.user,
        )

        with self.assertRaises(ValidationError):
            approve_monthly_report(
                report.pk,
                approved_by=self.user,
            )

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            ConsumptionRecordStatus.SUBMITTED,
        )
