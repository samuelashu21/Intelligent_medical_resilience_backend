from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.logistics.receiving_models import (
    ReceivingStatus,
)

from apps.logistics.receiving_services import (
    create_receiving_record,
    record_received_line,
    submit_receiving_record,
    approve_receiving_record,
    reject_receiving_record,
    post_receiving_record,
)


class ReceivingWorkflowTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Required fixtures:
        # cls.recipient_user
        # cls.approver
        # cls.posting_user
        # cls.delivered_shipment
        # cls.recipient_warehouse
        #
        # The shipment must have at least one shipment line.
        pass

    def create_receipt(self):

        return create_receiving_record(
            shipment_id=self.delivered_shipment.pk,
            receiving_warehouse=self.recipient_warehouse,
            user=self.recipient_user,
        )

    def test_receipt_created_only_for_delivered_shipment(self):

        self.delivered_shipment.status = "IN_TRANSIT"
        self.delivered_shipment.save(
            update_fields=["status"]
        )

        with self.assertRaises(ValidationError):
            self.create_receipt()

    def test_receipt_creates_lines_from_shipment(self):

        receipt = self.create_receipt()

        self.assertEqual(
            receipt.lines.count(),
            self.delivered_shipment.lines.count(),
        )

    def test_receipt_line_can_be_recorded(self):

        receipt = self.create_receipt()
        line = receipt.lines.first()

        updated = record_received_line(
            receiving_line_id=line.pk,
            physically_received_quantity="100",
            accepted_quantity="95",
            damaged_quantity="5",
            user=self.recipient_user,
        )

        self.assertEqual(
            updated.accepted_quantity,
            95,
        )

    def test_receipt_cannot_be_approved_by_creator(self):

        receipt = self.create_receipt()

        # Submit after recording all required lines.
        self.record_all_lines(receipt)

        submit_receiving_record(
            receiving_record_id=receipt.pk,
            user=self.recipient_user,
        )

        with self.assertRaises(ValidationError):
            approve_receiving_record(
                receiving_record_id=receipt.pk,
                user=self.recipient_user,
            )

    def test_receipt_cannot_be_posted_before_approval(self):

        receipt = self.create_receipt()

        with self.assertRaises(ValidationError):
            post_receiving_record(
                receiving_record_id=receipt.pk,
                user=self.posting_user,
            )

    def test_rejected_receipt_cannot_be_posted(self):

        receipt = self.create_receipt()

        self.record_all_lines(receipt)

        submit_receiving_record(
            receiving_record_id=receipt.pk,
            user=self.recipient_user,
        )

        reject_receiving_record(
            receiving_record_id=receipt.pk,
            user=self.approver,
            reason="Incorrect shipment inspection.",
        )

        receipt.refresh_from_db()

        self.assertEqual(
            receipt.status,
            ReceivingStatus.REJECTED,
        )

        with self.assertRaises(ValidationError):
            post_receiving_record(
                receiving_record_id=receipt.pk,
                user=self.posting_user,
            )

    def record_all_lines(self, receipt):
        """
        Populate valid quantities for every shipment line.
        Add a test-specific implementation using your actual
        shipment fixture quantities and medicine units.
        """
        raise NotImplementedError(
            "Implement this helper using the shipment fixture."
        )