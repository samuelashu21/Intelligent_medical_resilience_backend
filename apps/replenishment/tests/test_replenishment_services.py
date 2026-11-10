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

from apps.replenishment.models import (
    ReplenishmentRequest,
)

from apps.replenishment.services import (
    approve_replenishment_request,
    cancel_replenishment_request,
    create_replenishment_request,
    reject_replenishment_request,
    submit_replenishment_request,
)


class ReplenishmentWorkflowTests(TestCase):

    # ======================================================
    # TEST SETUP
    # ======================================================

    def setUp(self):

        # --------------------------------------------------
        # Organization Type
        # --------------------------------------------------

        self.organization_type = OrganizationUnitType.objects.create(
            code="REPL-ORG-TYPE",
            name="Replenishment Test Organization",
            description="Organization type for replenishment tests.",
            level=1,
        )

        # --------------------------------------------------
        # Organization
        # --------------------------------------------------

        self.organization = Organization.objects.create(
            code="REPL-ORG",
            name="Replenishment Organization",
            organization_type=self.organization_type,
        )

        # --------------------------------------------------
        # Facility Type
        # --------------------------------------------------

        self.facility_type = FacilityType.objects.create(
            code="REPL-HEALTH-CENTER",
            name="Replenishment Test Health Center",
            description="Facility type for replenishment workflow tests.",
        )

        # --------------------------------------------------
        # Facility
        # --------------------------------------------------

        self.facility = Facility.objects.create(
            code="REPL-FAC",
            name="Replenishment Facility",
            facility_type=self.facility_type,
            organization=self.organization,
        )

        # --------------------------------------------------
        # Dosage Form
        # --------------------------------------------------

        self.dosage_form = DosageForm.objects.create(
            code="REPL-TABLET",
            name="Replenishment Test Tablet",
            description="Tablet dosage form for replenishment tests.",
        )

        # --------------------------------------------------
        # Medicine
        # --------------------------------------------------

        self.medicine = Medicine.objects.create(
            code="REPL-MED",
            generic_name="Replenishment Medicine",
            dosage_form=self.dosage_form,
        )

        # --------------------------------------------------
        # Requester
        # --------------------------------------------------

        self.requester = User.objects.create_user(
            email="requester@example.test",
            username="requester",
            password="SecurePassword123!",
        )

        # --------------------------------------------------
        # Approver
        # --------------------------------------------------

        self.approver = User.objects.create_user(
            email="approver@example.test",
            username="approver",
            password="SecurePassword123!",
        )

    # ======================================================
    # REUSABLE REQUEST FACTORY
    # ======================================================

    def create_request(self):

        return create_replenishment_request(
            facility_id=self.facility.pk,
            requested_by=self.requester,
            justification=("Medicine stock is below the required level."),
            items=[
                {
                    "medicine_id": self.medicine.pk,
                    "requested_quantity": Decimal("500"),
                    "recommended_quantity": Decimal("450"),
                    "unit_code": "TABLET",
                    "reason": "Stock policy recommendation.",
                }
            ],
        )

    # ======================================================
    # TEST 1: CREATE DRAFT REQUEST
    # ======================================================

    def test_create_draft_request(self):

        request = self.create_request()

        self.assertEqual(
            request.status,
            ReplenishmentRequest.Status.DRAFT,
        )

        self.assertEqual(
            request.items.count(),
            1,
        )

        self.assertTrue(request.request_number.startswith("MR-"))

    # ======================================================
    # TEST 2: SUBMIT REQUEST
    # ======================================================

    def test_submit_request(self):

        request = self.create_request()

        result = submit_replenishment_request(
            request.pk,
            self.requester,
        )

        self.assertEqual(
            result.status,
            ReplenishmentRequest.Status.SUBMITTED,
        )

        self.assertIsNotNone(result.submitted_at)

    # ======================================================
    # TEST 3: ONLY REQUESTER CAN SUBMIT
    # ======================================================

    def test_only_requester_can_submit(self):

        request = self.create_request()

        with self.assertRaises(ValidationError):

            submit_replenishment_request(
                request.pk,
                self.approver,
            )

    # ======================================================
    # TEST 4: APPROVE REQUEST
    # ======================================================

    def test_approve_request(self):

        request = self.create_request()

        submit_replenishment_request(
            request.pk,
            self.requester,
        )

        line = request.items.get()

        result = approve_replenishment_request(
            request.pk,
            self.approver,
            {
                str(line.pk): "400",
            },
        )

        self.assertEqual(
            result.status,
            ReplenishmentRequest.Status.APPROVED,
        )

        line.refresh_from_db()

        self.assertEqual(
            line.approved_quantity,
            Decimal("400"),
        )

    # ======================================================
    # TEST 5: REQUESTER CANNOT APPROVE OWN REQUEST
    # ======================================================

    def test_requester_cannot_approve_own_request(self):

        request = self.create_request()

        submit_replenishment_request(
            request.pk,
            self.requester,
        )

        with self.assertRaises(ValidationError):

            approve_replenishment_request(
                request.pk,
                self.requester,
            )

    # ======================================================
    # TEST 6: REJECTION REQUIRES REASON
    # ======================================================

    def test_reject_request_requires_reason(self):

        request = self.create_request()

        submit_replenishment_request(
            request.pk,
            self.requester,
        )

        with self.assertRaises(ValidationError):

            reject_replenishment_request(
                request.pk,
                self.approver,
                "",
            )

    # ======================================================
    # TEST 7: REJECT REQUEST
    # ======================================================

    def test_reject_request(self):

        request = self.create_request()

        submit_replenishment_request(
            request.pk,
            self.requester,
        )

        result = reject_replenishment_request(
            request.pk,
            self.approver,
            "Please revise the requested quantity.",
        )

        self.assertEqual(
            result.status,
            ReplenishmentRequest.Status.REJECTED,
        )

    # ======================================================
    # TEST 8: CANCEL DRAFT REQUEST
    # ======================================================

    def test_cancel_draft_request(self):

        request = self.create_request()

        result = cancel_replenishment_request(
            request.pk,
            self.requester,
            "Request created in error.",
        )

        self.assertEqual(
            result.status,
            ReplenishmentRequest.Status.CANCELLED,
        )

    # ======================================================
    # TEST 9: CANNOT SUBMIT TWICE
    # ======================================================

    def test_cannot_submit_twice(self):

        request = self.create_request()

        submit_replenishment_request(
            request.pk,
            self.requester,
        )

        with self.assertRaises(ValidationError):

            submit_replenishment_request(
                request.pk,
                self.requester,
            )
