from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.redistribution.transfer_models import (
    TransferRequest,
    TransferRequestLine,
    TransferApprovalStage,
    TransferStatus,
)

from apps.redistribution.transfer_services import (
    submit_transfer_for_approval,
    approve_transfer,
    reject_transfer,
    cancel_transfer,
)


class TransferWorkflowTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Replace with your actual shared fixtures.
        # These objects must be created using your Phase 9,
        # Phase 15 and Phase 16 models.
        pass

    def create_transfer(self):

        transfer = TransferRequest.objects.create(
            donor_facility=self.facility_a,
            recipient_facility=self.facility_b,
            organization=self.facility_a.organization,
            requested_by=self.user,
            justification="Urgent medicine shortage.",
            status=TransferStatus.DRAFT,
        )

        TransferRequestLine.objects.create(
            transfer=transfer,
            medicine=self.medicine,
            batch=self.batch,
            requested_quantity=Decimal("100"),
            unit_code="UNIT",
        )

        return transfer

    def test_transfer_creation_starts_as_draft(self):

        transfer = self.create_transfer()

        self.assertEqual(
            transfer.status,
            TransferStatus.DRAFT,
        )

    def test_transfer_cannot_submit_without_approval_stage(self):

        transfer = self.create_transfer()

        with self.assertRaises(ValidationError):
            submit_transfer_for_approval(
                transfer_id=transfer.pk,
                user=self.user,
            )

    def test_transfer_submission_sets_first_approval_level(self):

        transfer = self.create_transfer()

        stage = TransferApprovalStage.objects.create(
            organization=transfer.organization,
            level=1,
            name="District Review",
            required_role_code="DISTRICT_OFFICER",
        )

        result = submit_transfer_for_approval(
            transfer_id=transfer.pk,
            user=self.user,
        )

        self.assertEqual(
            result.status,
            TransferStatus.SUBMITTED,
        )

        self.assertEqual(
            result.current_approval_level,
            stage.level,
        )

    def test_requester_cannot_approve_own_transfer(self):

        transfer = self.create_transfer()

        TransferApprovalStage.objects.create(
            organization=transfer.organization,
            level=1,
            name="District Review",
            required_role_code="DISTRICT_OFFICER",
        )

        submit_transfer_for_approval(
            transfer_id=transfer.pk,
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            approve_transfer(
                transfer_id=transfer.pk,
                user=self.user,
            )

    def test_rejected_transfer_cannot_be_approved(self):

        transfer = self.create_transfer()

        transfer.status = TransferStatus.REJECTED
        transfer.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            approve_transfer(
                transfer_id=transfer.pk,
                user=self.approver,
            )

    def test_cancelled_transfer_cannot_be_approved(self):

        transfer = self.create_transfer()

        transfer.status = TransferStatus.CANCELLED
        transfer.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            approve_transfer(
                transfer_id=transfer.pk,
                user=self.approver,
            )