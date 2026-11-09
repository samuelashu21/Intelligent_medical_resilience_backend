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
    BatchExpiryAlert,
    BatchLifecycleAction,
    BatchLifecycleEvent,
    BatchStatus,
    InventoryBalance,
    StockBatch,
)

from apps.inventory.batch_services import (
    dispose_batch,
    mark_batch_damaged,
    quarantine_batch,
    recall_batch,
    release_quarantined_batch,
    scan_batch_expiry,
)


class BatchLifecycleTests(TestCase):

    def setUp(self):
        today = timezone.localdate()

        self.user = User.objects.create_user(
            email="batch.lifecycle@example.test",
            username="batch_lifecycle",
            password="SecurePassword123!",
        )

        self.org_type = OrganizationUnitType.objects.create(
            code="HEALTH_FACILITY",
            name="Health Facility",
            level=2,
        )

        self.organization = Organization.objects.create(
            code="BATCH-LIFE-ORG",
            name="Batch Lifecycle Organization",
            organization_type=self.org_type,
        )

        self.warehouse = Warehouse.objects.create(
            code="BATCH-LIFE-WH",
            name="Batch Lifecycle Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
        )

        self.zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="BATCH-LIFE-ZONE",
            name="Ambient",
            storage_type=StorageType.AMBIENT,
        )

        self.location = StorageLocation.objects.create(
            zone=self.zone,
            code="BATCH-LIFE-LOC",
            name="Shelf",
        )

        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        self.medicine = Medicine.objects.create(
            code="BATCH-LIFE-MED",
            generic_name="Batch Lifecycle Medicine",
            dosage_form=self.dosage_form,
        )

        self.batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.location,
            batch_number="BATCH-LIFE-001",
            manufacture_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=365),
            status=BatchStatus.AVAILABLE,
        )

        self.balance = InventoryBalance.objects.create(
            batch=self.batch,
            quantity_on_hand=Decimal("100"),
            quantity_reserved=Decimal("0"),
        )

    def test_quarantine_batch(self):
        batch = quarantine_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Quality inspection required.",
        )

        self.assertEqual(
            batch.status,
            BatchStatus.QUARANTINED,
        )

        self.assertTrue(
            BatchLifecycleEvent.objects.filter(
                batch=batch,
                action=BatchLifecycleAction.QUARANTINED,
            ).exists()
        )

    def test_release_quarantined_batch(self):
        quarantine_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Quality inspection required.",
        )

        batch = release_quarantined_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Quality inspection passed.",
        )

        self.assertEqual(
            batch.status,
            BatchStatus.AVAILABLE,
        )

    def test_expired_batch_cannot_be_released(self):
        quarantine_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Quality inspection.",
        )

        past_date = timezone.localdate() - timedelta(days=1)
        StockBatch.objects.filter(pk=self.batch.pk).update(expiry_date=past_date)
        self.batch.refresh_from_db()

        with self.assertRaises(ValidationError):
            release_quarantined_batch(
                batch_id=self.batch.pk,
                performed_by=self.user,
                reason="Attempted release.",
            )

    def test_mark_batch_damaged(self):
        batch = mark_batch_damaged(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Packaging damaged.",
        )

        self.assertEqual(
            batch.status,
            BatchStatus.DAMAGED,
        )

    def test_recall_batch(self):
        batch = recall_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Manufacturer recall notice.",
            reference_number="RECALL-2026-001",
        )

        self.assertEqual(
            batch.status,
            BatchStatus.RECALLED,
        )

    def test_disposal_requires_zero_stock(self):
        quarantine_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Failed quality inspection.",
        )

        with self.assertRaises(ValidationError):
            dispose_batch(
                batch_id=self.batch.pk,
                performed_by=self.user,
                reason="Disposal requested.",
            )

    def test_disposal_after_stock_is_removed(self):
        quarantine_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Failed quality inspection.",
        )

        self.balance.quantity_on_hand = Decimal("0")
        self.balance.save(update_fields=["quantity_on_hand"])

        batch = dispose_batch(
            batch_id=self.batch.pk,
            performed_by=self.user,
            reason="Authorized disposal completed.",
        )

        self.assertEqual(
            batch.status,
            BatchStatus.DISPOSED,
        )

    def test_expiry_scan_creates_alert(self):
        future_date = timezone.localdate() + timedelta(days=20)
        StockBatch.objects.filter(pk=self.batch.pk).update(expiry_date=future_date)
        self.batch.refresh_from_db()

        result = scan_batch_expiry()

        self.assertGreaterEqual(
            result["created_alerts"],
            1,
        )

        self.assertTrue(
            BatchExpiryAlert.objects.filter(
                batch=self.batch,
                alert_level=BatchExpiryAlert.AlertLevel.CRITICAL,
                is_active=True,
            ).exists()
        )

    def test_expiry_scan_marks_expired_batch(self):
        past_date = timezone.localdate() - timedelta(days=1)
        StockBatch.objects.filter(pk=self.batch.pk).update(expiry_date=past_date)
        self.batch.refresh_from_db()

        scan_batch_expiry()

        self.batch.refresh_from_db()

        self.assertEqual(
            self.batch.status,
            BatchStatus.EXPIRED,
        )

        self.assertTrue(
            BatchLifecycleEvent.objects.filter(
                batch=self.batch,
                action=BatchLifecycleAction.MARKED_EXPIRED,
                performed_by__isnull=True,
            ).exists()
        )

    def test_expiry_scan_is_idempotent(self):
        future_date = timezone.localdate() + timedelta(days=20)
        StockBatch.objects.filter(pk=self.batch.pk).update(expiry_date=future_date)
        self.batch.refresh_from_db()

        scan_batch_expiry()
        scan_batch_expiry()

        active_alerts = BatchExpiryAlert.objects.filter(
            batch=self.batch,
            is_active=True,
        ).count()

        self.assertEqual(active_alerts, 1)