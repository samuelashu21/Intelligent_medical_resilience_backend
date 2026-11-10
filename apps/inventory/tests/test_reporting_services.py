from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)
from apps.facilities.models import Facility, FacilityType
from apps.medicines.models import Medicine, DosageForm
from apps.warehouses.models import (
    Warehouse,
    WarehouseType,
    StorageZone,
    StorageLocation,
    StorageType,
)
from apps.inventory.models import (
    InventoryBalance,
    StockBatch,
)

from apps.inventory.reporting_services import (
    get_available_quantity,
    get_expiry_report,
    get_facility_stock_summary,
    get_medicine_stock_status,
)


class StockReportingTests(TestCase):

    def setUp(self):
        # --------------------------------------------------
        # Organization
        # --------------------------------------------------
        self.organization_type = OrganizationUnitType.objects.create(
            code="REPORT-ORG-TYPE",
            name="Reporting Organization Type",
            level=1,
        )

        self.organization = Organization.objects.create(
            code="REPORT-ORG",
            name="Reporting Organization",
            organization_type=self.organization_type,
        )

        # --------------------------------------------------
        # Facility
        # --------------------------------------------------
        self.facility_type = FacilityType.objects.create(
            code="REPORT-FAC-TYPE",
            name="Reporting Health Facility",
        )

        self.facility = Facility.objects.create(
            code="REPORT-FAC",
            name="Reporting Facility",
            organization=self.organization,
            facility_type=self.facility_type,
        )

        # --------------------------------------------------
        # Warehouse
        # --------------------------------------------------
        self.warehouse = Warehouse.objects.create(
            code="REPORT-WH",
            name="Reporting Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
            facility=self.facility,
        )

        # --------------------------------------------------
        # Storage zone and location
        # --------------------------------------------------
        self.storage_zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="REPORT-ZONE",
            name="Reporting Storage Zone",
            storage_type=StorageType.AMBIENT,
        )

        self.storage_location = StorageLocation.objects.create(
            zone=self.storage_zone,
            code="REPORT-LOC",
            name="Reporting Storage Location",
        )

        # --------------------------------------------------
        # Medicine
        # --------------------------------------------------
        self.dosage_form = DosageForm.objects.create(
            code="REPORT-TABLET",
            name="Reporting Tablet",
        )

        self.medicine = Medicine.objects.create(
            code="REPORT-MED",
            generic_name="Reporting Medicine",
            dosage_form=self.dosage_form,
        )

    def create_balance(
        self,
        batch_number,
        quantity,
        reserved=0,
        expiry_days=365,
    ):
        today = timezone.localdate()

        # Always create a batch that is valid at receipt time.
        # Expired batches are simulated after creation below.
        batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.storage_location,
            batch_number=batch_number,
            received_date=today,
            expiry_date=today + timedelta(days=max(expiry_days, 1)),
        )

        # Simulate an existing batch becoming expired.
        # QuerySet.update() intentionally avoids the creation-time
        # validation that prevents receiving an already expired batch.
        if expiry_days < 0:
            StockBatch.objects.filter(pk=batch.pk).update(
                expiry_date=today + timedelta(days=expiry_days)
            )
            batch.refresh_from_db()

        balance = InventoryBalance.objects.create(
            batch=batch,
            quantity_on_hand=Decimal(str(quantity)),
            quantity_reserved=Decimal(str(reserved)),
        )

        return balance

    def test_available_quantity(self):
        balance = self.create_balance(
            "REPORT-BATCH-001",
            100,
            20,
        )

        self.assertEqual(
            get_available_quantity(balance),
            Decimal("80"),
        )

    def test_expired_batch_not_available(self):
        balance = self.create_balance(
            "REPORT-BATCH-002",
            100,
            0,
            expiry_days=-1,
        )

        self.assertEqual(
            get_available_quantity(balance),
            Decimal("0"),
        )

    def test_facility_stock_summary(self):
        self.create_balance(
            "REPORT-BATCH-003",
            100,
            20,
        )

        result = get_facility_stock_summary(
            facility_id=self.facility.pk,
        )

        self.assertEqual(
            Decimal(result["total_on_hand"]),
            Decimal("100"),
        )
        self.assertEqual(
            Decimal(result["total_reserved"]),
            Decimal("20"),
        )
        self.assertEqual(
            Decimal(result["total_available"]),
            Decimal("80"),
        )

    def test_stock_status_without_consumption_history(self):
        self.create_balance(
            "REPORT-BATCH-004",
            100,
        )

        rows = get_medicine_stock_status(
            facility_id=self.facility.pk,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["status"],
            "NO_CONSUMPTION_HISTORY",
        )

    def test_expiry_report_includes_near_expiry_batch(self):
        self.create_balance(
            "REPORT-BATCH-005",
            100,
            expiry_days=30,
        )

        result = get_expiry_report(
            facility_id=self.facility.pk,
            days=90,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["status"],
            "NEAR_EXPIRY",
        )

    def test_expiry_report_identifies_expired_batch(self):
        self.create_balance(
            "REPORT-BATCH-006",
            100,
            expiry_days=-5,
        )

        result = get_expiry_report(
            facility_id=self.facility.pk,
            days=90,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["status"],
            "EXPIRED",
        )
