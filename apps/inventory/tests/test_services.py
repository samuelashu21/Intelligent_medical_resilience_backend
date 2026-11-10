from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationUnitType
from apps.medicines.models import DosageForm, Medicine
from apps.warehouses.models import (
    StorageLocation,
    StorageType,
    StorageZone,
    Warehouse,
    WarehouseType,
)

from apps.inventory.models import (
    InventoryBalance,
    MovementType,
    ReservationStatus,
    StockBatch,
    StockMovement,
)

from apps.inventory.services import (
    adjust_stock,
    fulfill_reservation,
    get_fefo_batches,
    get_stock_balance,
    issue_stock,
    receive_stock,
    release_reservation,
    reserve_stock,
)


class InventoryServiceTests(TestCase):

    def setUp(self):
        # 1. Create OrganizationUnitType and Organization
        self.org_type = OrganizationUnitType.objects.create(
            code="HEALTH_FACILITY",
            name="Health Facility",
            level=2,
        )

        self.organization = Organization.objects.create(
            code="INV-SERVICE-ORG",
            name="Inventory Service Organization",
            organization_type=self.org_type,
        )

        self.user = User.objects.create_user(
            email="inventory.service@example.test",
            username="inventory_service",
            password="SecurePassword123!",
        )

        self.warehouse = Warehouse.objects.create(
            code="INV-SERVICE-WH",
            name="Inventory Service Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
        )

        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="INV-SERVICE-ZONE",
            name="Ambient",
            storage_type=StorageType.AMBIENT,
        )

        self.location = StorageLocation.objects.create(
            zone=self.zone,
            code="INV-SERVICE-LOC",
            name="Shelf",
        )

        # 2. Create DosageForm and Medicine
        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        self.medicine = Medicine.objects.create(
            code="INV-SERVICE-MED",
            generic_name="Service Test Medicine",
            dosage_form=self.dosage_form,
        )

        self.batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.location,
            batch_number="SERVICE-BATCH-001",
            expiry_date=timezone.localdate() + timedelta(days=365),
        )

        InventoryBalance.objects.create(batch=self.batch)

    def test_receive_stock(self):
        movement = receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        balance = self.batch.balance
        balance.refresh_from_db()  # Refresh from database to get updated quantity

        self.assertEqual(
            movement.movement_type,
            MovementType.RECEIPT,
        )

        self.assertEqual(
            balance.quantity_on_hand,
            Decimal("100"),
        )

    def test_issue_stock(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        issue_stock(
            batch_id=self.batch.pk,
            quantity=30,
            performed_by=self.user,
        )

        self.batch.balance.refresh_from_db()

        self.assertEqual(
            self.batch.balance.quantity_on_hand,
            Decimal("70"),
        )

    def test_issue_cannot_exceed_available_stock(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=10,
            performed_by=self.user,
        )

        with self.assertRaises(ValidationError):
            issue_stock(
                batch_id=self.batch.pk,
                quantity=20,
                performed_by=self.user,
            )

    def test_quarantined_batch_cannot_be_issued(self):
        from apps.inventory.batch_services import quarantine_batch
        from apps.inventory.models import BatchStatus

        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        quarantine_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Quality inspection.",
        )

        with self.assertRaises(ValidationError):
            issue_stock(
                batch_id=self.batch.pk,
                quantity=10,
                performed_by=self.user,
            )

        self.batch.refresh_from_db()

        self.assertEqual(
            self.batch.status,
            BatchStatus.QUARANTINED,
        )

        self.batch.balance.refresh_from_db()

        self.assertEqual(
            self.batch.balance.quantity_on_hand,
            Decimal("100"),
        )


def test_expired_batch_cannot_be_issued(self):
    # First receive stock while the batch is still valid.
    receive_stock(
        batch_id=self.batch.pk,
        quantity=100,
        performed_by=self.user,
    )

    # Simulate the batch expiring after stock has been received.
    past_date = timezone.localdate() - timedelta(days=1)

    StockBatch.objects.filter(pk=self.batch.pk).update(expiry_date=past_date)

    self.batch.refresh_from_db()

    # Verify that issuing expired stock is rejected.
    with self.assertRaises(ValidationError):
        issue_stock(
            batch_id=self.batch.pk,
            quantity=10,
            performed_by=self.user,
        )

    # Verify that the failed issue did not change stock.
    self.batch.balance.refresh_from_db()

    self.assertEqual(
        self.batch.balance.quantity_on_hand,
        Decimal("100"),
    )

    # Verify that no issue movement was recorded.
    self.assertFalse(
        StockMovement.objects.filter(
            batch=self.batch,
            movement_type=MovementType.ISSUE,
        ).exists()
    )

    def test_adjustment_in(self):
        adjust_stock(
            batch_id=self.batch.pk,
            quantity=25,
            direction="IN",
            performed_by=self.user,
            reason="Verified additional stock.",
        )

        self.batch.balance.refresh_from_db()

        self.assertEqual(
            self.batch.balance.quantity_on_hand,
            Decimal("25"),
        )

    def test_adjustment_out(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        adjust_stock(
            batch_id=self.batch.pk,
            quantity=20,
            direction="OUT",
            performed_by=self.user,
            reason="Physical count discrepancy.",
        )

        self.batch.balance.refresh_from_db()

        self.assertEqual(
            self.batch.balance.quantity_on_hand,
            Decimal("80"),
        )

    def test_reserve_stock(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        reservation = reserve_stock(
            batch_id=self.batch.pk,
            quantity=40,
            reference_number="REQ-001",
            reserved_by=self.user,
        )

        self.batch.balance.refresh_from_db()

        self.assertEqual(
            self.batch.balance.quantity_on_hand,
            Decimal("100"),
        )

        self.assertEqual(
            self.batch.balance.quantity_reserved,
            Decimal("40"),
        )

        self.assertEqual(
            self.batch.balance.quantity_available,
            Decimal("60"),
        )

        self.assertEqual(reservation.status, ReservationStatus.ACTIVE)

    def test_release_reservation(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        reservation = reserve_stock(
            batch_id=self.batch.pk,
            quantity=40,
            reference_number="REQ-002",
            reserved_by=self.user,
        )

        release_reservation(reservation_id=reservation.pk)

        self.batch.balance.refresh_from_db()
        reservation.refresh_from_db()

        self.assertEqual(
            self.batch.balance.quantity_reserved,
            Decimal("0"),
        )

        self.assertEqual(
            reservation.status,
            ReservationStatus.RELEASED,
        )

    def test_fulfill_reservation(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        reservation = reserve_stock(
            batch_id=self.batch.pk,
            quantity=30,
            reference_number="REQ-003",
            reserved_by=self.user,
        )

        movement = fulfill_reservation(
            reservation_id=reservation.pk,
            performed_by=self.user,
        )

        self.batch.balance.refresh_from_db()
        reservation.refresh_from_db()

        self.assertEqual(
            movement.movement_type,
            MovementType.ISSUE,
        )

        self.assertEqual(
            self.batch.balance.quantity_on_hand,
            Decimal("70"),
        )

        self.assertEqual(
            self.batch.balance.quantity_reserved,
            Decimal("0"),
        )

        self.assertEqual(
            reservation.status,
            ReservationStatus.FULFILLED,
        )

    def test_fefo_orders_earliest_expiry_first(self):
        receive_stock(
            batch_id=self.batch.pk,
            quantity=100,
            performed_by=self.user,
        )

        later_batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.location,
            batch_number="SERVICE-BATCH-002",
            expiry_date=timezone.localdate() + timedelta(days=500),
        )

        InventoryBalance.objects.create(
            batch=later_batch,
            quantity_on_hand=50,
        )

        batches = get_fefo_batches(
            medicine_id=self.medicine.pk,
            warehouse_id=self.warehouse.pk,
        )

        self.assertEqual(
            batches[0].batch_number,
            "SERVICE-BATCH-001",
        )

    def test_balance_without_receipts_is_zero(self):
        result = get_stock_balance(self.batch)

        self.assertEqual(result["on_hand"], Decimal("0"))
        self.assertEqual(result["available"], Decimal("0"))
