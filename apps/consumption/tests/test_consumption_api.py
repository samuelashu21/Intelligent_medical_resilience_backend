
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import (
    User,
    AccessPermission,
    Role,
    RolePermission,
    UserRole,
)

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


class ConsumptionAPITests(TestCase):

    def setUp(self):
        # ==================================================
        # API CLIENT
        # ==================================================

        self.client = APIClient()

        # ==================================================
        # TEST USER
        # ==================================================

        self.user = User.objects.create_user(
            email="api.pharmacist@example.test",
            username="api_pharmacist",
            password="SecurePassword123!",
        )

        # ==================================================
        # ORGANIZATION TYPE
        # ==================================================

        self.organization_type = OrganizationUnitType.objects.create(
            code="API-CONS-ORG-TYPE",
            name="API Consumption Organization Type",
            level=1,
        )

        # ==================================================
        # ORGANIZATION
        # ==================================================

        self.organization = Organization.objects.create(
            code="API-CONS-ORG",
            name="API Consumption Organization",
            organization_type=self.organization_type,
        )

        # ==================================================
        # FACILITY TYPE
        # ==================================================

        self.facility_type = FacilityType.objects.create(
            code="API-CONS-FAC",
            name="Health Center",
        )

        # ==================================================
        # FACILITY
        # ==================================================

        self.facility = Facility.objects.create(
            code="API-CONS-001",
            name="API Consumption Facility",
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
            code="API-CONS-MED",
            generic_name="API Test Medicine",
            dosage_form=self.dosage_form,
        )

        # ==================================================
        # PERMISSIONS
        # ==================================================

        self.create_permission = AccessPermission.objects.create(
            code="consumption.create",
            name="Record Medicine Consumption",
            module="consumption",
        )

        self.view_permission = AccessPermission.objects.create(
            code="consumption.view",
            name="View Medicine Consumption",
            module="consumption",
        )

        # ==================================================
        # ROLE
        # ==================================================

        self.role = Role.objects.create(
            code="CONSUMPTION_TESTER",
            name="Consumption Tester",
        )

        # ==================================================
        # ROLE PERMISSIONS
        # ==================================================

        RolePermission.objects.create(
            role=self.role,
            permission=self.create_permission,
        )

        RolePermission.objects.create(
            role=self.role,
            permission=self.view_permission,
        )

        # ==================================================
        # USER ROLE ASSIGNMENT
        # ==================================================

        UserRole.objects.create(
            user=self.user,
            role=self.role,
            organization=self.organization,
        )

        # ==================================================
        # AUTHENTICATED CLIENT
        # ==================================================

        self.client.force_authenticate(
            user=self.user,
        )

    # ======================================================
    # CREATE DAILY CONSUMPTION
    # ======================================================

    def test_create_daily_consumption(self):

        response = self.client.post(
            "/api/v1/consumption/daily/",
            {
                "facility": str(self.facility.pk),
                "medicine": str(self.medicine.pk),
                "consumption_date": "2026-10-05",
                "quantity": "50",
                "unit_code": "TABLET",
                "source": "DISPENSING",
                "reporting_method": "DAILY",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
            response.data,
        )

        self.assertEqual(
            response.data["quantity"],
            "50.000",
        )

    # ======================================================
    # ANONYMOUS USER CANNOT RECORD CONSUMPTION
    # ======================================================

    def test_anonymous_user_cannot_record_consumption(self):

        self.client.force_authenticate(
            user=None,
        )

        response = self.client.post(
            "/api/v1/consumption/daily/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
            response.data,
        )
