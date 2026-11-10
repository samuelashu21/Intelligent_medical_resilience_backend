from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.logistics.shipment_models import (
    Shipment,
    ShipmentStatus,
    ShipmentEvent,
    ShipmentEventType,
    VehicleStatus,
)

from apps.logistics.shipment_services import (
    create_shipment,
    mark_shipment_ready,
    update_shipment_tracking,
    report_shipment_delay,
    report_shipment_exception,
    report_shipment_delivered,
)


class ShipmentWorkflowTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Implement using your existing Phase 9,
        # Phase 13, Phase 14, Phase 15, Phase 16
        # and Phase 27 test fixtures.
        #
        # Required objects:
        # cls.user
        # cls.transfer (status RESERVED)
        # cls.transporter (ACTIVE)
        # cls.vehicle (AVAILABLE)
        pass

    def test_shipment_creation_does_not_dispatch_stock(self):

        shipment = create_shipment(
            transfer_id=self.transfer.pk,
            transporter_id=self.transporter.pk,
            vehicle_id=self.vehicle.pk,
            driver_name="Test Driver",
            user=self.user,
        )

        self.assertEqual(
            shipment.status,
            ShipmentStatus.DRAFT,
        )

        self.transfer.refresh_from_db()

        self.assertEqual(
            self.transfer.status,
            "RESERVED",
        )

    def test_shipment_creation_assigns_vehicle(self):

        shipment = create_shipment(
            transfer_id=self.transfer.pk,
            transporter_id=self.transporter.pk,
            vehicle_id=self.vehicle.pk,
            driver_name="Test Driver",
            user=self.user,
        )

        self.vehicle.refresh_from_db()

        self.assertEqual(
            self.vehicle.status,
            VehicleStatus.ASSIGNED,
        )

    def test_only_reserved_transfer_can_create_shipment(self):

        self.transfer.status = "SUBMITTED"
        self.transfer.save(update_fields=["status"])

        with self.assertRaises(ValidationError):

            create_shipment(
                transfer_id=self.transfer.pk,
                transporter_id=self.transporter.pk,
                vehicle_id=self.vehicle.pk,
                driver_name="Test Driver",
                user=self.user,
            )

    def test_shipment_ready_requires_reserved_stock(self):

        shipment = create_shipment(
            transfer_id=self.transfer.pk,
            transporter_id=self.transporter.pk,
            vehicle_id=self.vehicle.pk,
            driver_name="Test Driver",
            user=self.user,
        )

        # Reduce the reservation to make the shipment invalid.
        line = shipment.lines.first()
        line.transfer_line.reserved_quantity = 0
        line.transfer_line.save(
            update_fields=["reserved_quantity"]
        )

        with self.assertRaises(ValidationError):
            mark_shipment_ready(
                shipment_id=shipment.pk,
                user=self.user,
            )

    def test_tracking_rejected_before_dispatch(self):

        shipment = create_shipment(
            transfer_id=self.transfer.pk,
            transporter_id=self.transporter.pk,
            vehicle_id=self.vehicle.pk,
            driver_name="Test Driver",
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            update_shipment_tracking(
                shipment_id=shipment.pk,
                user=self.user,
                event_type=ShipmentEventType.IN_TRANSIT,
            )

    def test_delivery_rejected_before_dispatch(self):

        shipment = create_shipment(
            transfer_id=self.transfer.pk,
            transporter_id=self.transporter.pk,
            vehicle_id=self.vehicle.pk,
            driver_name="Test Driver",
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            report_shipment_delivered(
                shipment_id=shipment.pk,
                user=self.user,
            )

    def test_delay_creates_exception(self):

        shipment = self.create_dispatched_shipment()

        report_shipment_delay(
            shipment_id=shipment.pk,
            user=self.user,
            description="Road disruption.",
        )

        self.assertTrue(
            shipment.exceptions.filter(
                exception_type="DELAY",
                resolved=False,
            ).exists()
        )

    def test_exception_is_recorded(self):

        shipment = self.create_dispatched_shipment()

        exception = report_shipment_exception(
            shipment_id=shipment.pk,
            user=self.user,
            exception_type="DAMAGE",
            description="Outer packaging damaged.",
        )

        self.assertFalse(exception.resolved)

    def create_dispatched_shipment(self):
        """
        Use your actual Phase 15 stock movement adapter
        to create a real dispatched shipment fixture.
        """
        raise NotImplementedError(
            "Build this fixture using the Phase 15 dispatch ledger integration."
        )