
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

from apps.medicines.models import (
    DosageForm,
    Medicine,
)

from apps.warehouses.models import (
    StorageLocation,
    StorageType,
    StorageZone,
    Warehouse,
    WarehouseType,
)

from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
    StockCountLine,
    StockCountStatus,
)

from apps.inventory.reconciliation_services import (
    approve_stock_count,
    create_stock_count,
    post_stock_reconciliation,
    record_physical_count,
    start_stock_count,
    submit_stock_count,
)


class StockReconciliationTests(TestCase):

    def setUp(self):
        today = timezone.localdate()

        # --------------------------------------------------
        # 1. Users
        # --------------------------------------------------
        self.creator = User.objects.create_user(
            email="count.creator@example.test",
            username="count_creator",
            password="SecurePassword123!",
        )

        self.counter = User.objects.create_user(
            email="count.counter@example.test",
            username="count_counter",
            password="SecurePassword123!",
        )

        self.approver = User.objects.create_user(
            email="count.approver@example.test",
            username="count_approver",
            password="SecurePassword123!",
        )

        self.poster = User.objects.create_user(
            email="count.poster@example.test",
            username="count_poster",
            password="SecurePassword123!",
        )

        # --------------------------------------------------
        # 2. Organization type
        # --------------------------------------------------
        self.organization_type = OrganizationUnitType.objects.create(
            code="RECON-ORG-TYPE",
            name="Reconciliation Organization Type",
            level=2,
        )

        # --------------------------------------------------
        # 3. Organization
        # --------------------------------------------------
        self.organization = Organization.objects.create(
            code="RECON-ORG",
            name="Reconciliation Organization",
            organization_type=self.organization_type,
        )

        # --------------------------------------------------
        # 4. Warehouse
        # --------------------------------------------------
        self.warehouse = Warehouse.objects.create(
            code="RECON-WH",
            name="Reconciliation Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
        )

        # --------------------------------------------------
        # 5. Storage zone
        # --------------------------------------------------
        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="RECON-ZONE",
            name="Ambient",
            storage_type=StorageType.AMBIENT,
        )

        # --------------------------------------------------
        # 6. Storage location
        # --------------------------------------------------
        self.location = StorageLocation.objects.create(
            zone=self.zone,
            code="RECON-LOC",
            name="Shelf",
        )

        # --------------------------------------------------
        # 7. Dosage form
        # Medicine.dosage_form is a ForeignKey to DosageForm.
        # Do not pass "TABLET" directly to Medicine.
        # --------------------------------------------------
        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        # --------------------------------------------------
        # 8. Medicine
        # --------------------------------------------------
        self.medicine = Medicine.objects.create(
            code="RECON-MED",
            generic_name="Reconciliation Medicine",
            dosage_form=self.dosage_form,
        )

        # --------------------------------------------------
        # 9. Stock batch
        # --------------------------------------------------
        self.batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.location,
            batch_number="RECON-BATCH-001",
            manufacture_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=365),
        )

        # --------------------------------------------------
        # 10. Inventory balance
        # --------------------------------------------------
        self.balance = InventoryBalance.objects.create(
            batch=self.batch,
            quantity_on_hand=Decimal("100"),
            quantity_reserved=Decimal("0"),
        )

    # ======================================================
    # Helper method
    # ======================================================
    def create_and_start_count(self):
        count = create_stock_count(
            warehouse_id=self.warehouse.pk,
            reference_number="RECON-COUNT-001",
            created_by=self.creator,
        )

        start_stock_count(count.pk)

        return count

    # ======================================================
    # TEST 1: Stock count captures system balance
    # ======================================================
    def test_create_stock_count_captures_system_balance(self):
        count = self.create_and_start_count()

        line = count.lines.get(batch=self.batch)

        self.assertEqual(
            line.system_quantity,
            Decimal("100"),
        )

    # ======================================================
    # TEST 2: Record physical count
    # ======================================================
    def test_record_physical_count(self):
        count = self.create_and_start_count()

        line = count.lines.get(batch=self.batch)

        line = record_physical_count(
            line_id=line.pk,
            physical_quantity=95,
            counted_by=self.counter,
            reason="COUNTING_ERROR",
            explanation="Five units could not be located.",
        )

        self.assertEqual(
            line.variance,
            Decimal("-5"),
        )

    # ======================================================
    # TEST 3: Variance requires reason
    # ======================================================
    def test_variance_requires_reason(self):
        count = self.create_and_start_count()

        line = count.lines.get(batch=self.batch)

        with self.assertRaises(ValidationError):
            record_physical_count(
                line_id=line.pk,
                physical_quantity=95,
                counted_by=self.counter,
            )

    # ======================================================
    # TEST 4: Cannot submit count with missing lines
    # ======================================================
    def test_count_cannot_be_submitted_with_missing_lines(self):
        count = self.create_and_start_count()

        with self.assertRaises(ValidationError):
            submit_stock_count(
                count.pk,
                submitted_by=self.creator,
            )

    # ======================================================
    # TEST 5: Creator cannot approve own count
    # ======================================================
    def test_creator_cannot_approve_own_count(self):
        count = self.create_and_start_count()

        line = count.lines.get(batch=self.batch)

        record_physical_count(
            line_id=line.pk,
            physical_quantity=100,
            counted_by=self.counter,
        )

        submit_stock_count(
            count.pk,
            submitted_by=self.creator,
        )

        with self.assertRaises(ValidationError):
            approve_stock_count(
                count.pk,
                approved_by=self.creator,
            )

    # ======================================================
    # TEST 6: Posting reconciliation updates balance
    # ======================================================
    def test_reconciliation_posting_updates_balance(self):
        count = self.create_and_start_count()

        line = count.lines.get(batch=self.batch)

        record_physical_count(
            line_id=line.pk,
            physical_quantity=110,
            counted_by=self.counter,
            reason="UNRECORDED_RECEIPT",
            explanation=(
                "Ten units were found without a receipt record."
            ),
        )

        submit_stock_count(
            count.pk,
            submitted_by=self.creator,
        )

        approve_stock_count(
            count.pk,
            approved_by=self.approver,
        )

        post_stock_reconciliation(
            count.pk,
            posted_by=self.poster,
        )

        self.balance.refresh_from_db()
        count.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            Decimal("110"),
        )

        self.assertEqual(
            count.status,
            StockCountStatus.POSTED,
        )

    # ======================================================
    # TEST 7: Stale snapshot prevents posting
    # ======================================================
    def test_stale_snapshot_prevents_posting(self):
        count = self.create_and_start_count()

        line = count.lines.get(batch=self.batch)

        record_physical_count(
            line_id=line.pk,
            physical_quantity=95,
            counted_by=self.counter,
            reason="LOSS",
            explanation="Five units missing.",
        )

        submit_stock_count(
            count.pk,
            submitted_by=self.creator,
        )

        approve_stock_count(
            count.pk,
            approved_by=self.approver,
        )

        # Simulate a stock movement after the physical
        # count snapshot was captured.
        self.balance.quantity_on_hand = Decimal("120")

        self.balance.save(
            update_fields=["quantity_on_hand"],
        )

        with self.assertRaises(ValidationError):
            post_stock_reconciliation(
                count.pk,
                posted_by=self.poster,
            )

    # ======================================================
    # TEST 8: Count line cannot reference another warehouse
    # ======================================================
    
def test_count_line_cannot_reference_other_warehouse_batch(self):
    other_warehouse = Warehouse.objects.create(
        code="RECON-WH-OTHER",
        name="Other Warehouse",
        warehouse_type=WarehouseType.CENTRAL,
        organization=self.organization,
    )

    other_zone = StorageZone.objects.create(
        warehouse=other_warehouse,
        code="RECON-ZONE-OTHER",
        name="Other Ambient",
        storage_type=StorageType.AMBIENT,
    )

    other_location = StorageLocation.objects.create(
        zone=other_zone,
        code="RECON-LOC-OTHER",
        name="Other Shelf",
    )

    other_batch = StockBatch.objects.create(
        medicine=self.medicine,
        warehouse=other_warehouse,
        location=other_location,
        batch_number="RECON-BATCH-OTHER",
        manufacture_date=timezone.localdate() - timedelta(days=30),
        expiry_date=timezone.localdate() + timedelta(days=365),
    )

    count = self.create_and_start_count()

    with self.assertRaises(ValidationError):
        StockCountLine.objects.create(
            stock_count=count,
            batch=other_batch,
            system_quantity=0,
        )
