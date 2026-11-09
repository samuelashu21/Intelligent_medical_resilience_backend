
from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

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

from apps.warehouses.models import (
    Warehouse,
    WarehouseType,
    StorageZone,
    StorageLocation,
    StorageType,
)

from apps.inventory.models import (
    StockBatch,
    InventoryBalance,
    StockPolicy,
)

from apps.inventory.stock_policy_services import (
    calculate_daily_demand,
    calculate_reorder_point,
    calculate_target_stock,
    evaluate_stock_policy,
)


# ==========================================================
# STOCK POLICY CALCULATION TESTS
# ==========================================================

class StockPolicyCalculationTests(TestCase):

    def test_daily_demand(self):
        result = calculate_daily_demand(
            Decimal("300")
        )

        self.assertEqual(
            result,
            Decimal("10"),
        )

    def test_reorder_point(self):
        result = calculate_reorder_point(
            daily_demand=Decimal("10"),
            lead_time_days=20,
            safety_stock=Decimal("50"),
        )

        self.assertEqual(
            result,
            Decimal("250"),
        )

    def test_target_stock(self):
        result = calculate_target_stock(
            daily_demand=Decimal("10"),
            lead_time_days=20,
            review_period_days=30,
            safety_stock=Decimal("50"),
        )

        self.assertEqual(
            result,
            Decimal("550"),
        )


# ==========================================================
# STOCK POLICY MODEL TESTS
# ==========================================================

class StockPolicyModelTests(TestCase):

    def setUp(self):

        # --------------------------------------------------
        # Organization Type
        # --------------------------------------------------

        self.organization_type = OrganizationUnitType.objects.create(
            code="POLICY-ORG-TYPE",
            name="Policy Test Organization Type",
            level=1,
        )

        # --------------------------------------------------
        # Organization
        # --------------------------------------------------

        self.organization = Organization.objects.create(
            code="POLICY-ORG",
            name="Policy Test Organization",
            organization_type=self.organization_type,
        )

        # --------------------------------------------------
        # Facility Type
        # --------------------------------------------------

        self.facility_type = FacilityType.objects.create(
            code="POLICY-HOSPITAL",
            name="Policy Test Hospital",
        )

        # --------------------------------------------------
        # Facility
        # --------------------------------------------------

        self.facility = Facility.objects.create(
            code="POLICY-FAC",
            name="Policy Test Facility",
            organization=self.organization,
            facility_type=self.facility_type,
        )

        # --------------------------------------------------
        # Dosage Form
        # --------------------------------------------------

        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        # --------------------------------------------------
        # Medicine
        # --------------------------------------------------

        self.medicine = Medicine.objects.create(
            code="POLICY-MED",
            generic_name="Policy Test Medicine",
            dosage_form=self.dosage_form,
        )

    def test_create_facility_policy(self):

        policy = StockPolicy.objects.create(
            policy_level="FACILITY",
            organization=self.organization,
            facility=self.facility,
            medicine=self.medicine,
            minimum_stock=Decimal("100"),
            maximum_stock=Decimal("1000"),
            safety_stock=Decimal("50"),
            buffer_stock=Decimal("20"),
            lead_time_days=15,
            review_period_days=30,
        )

        self.assertEqual(
            policy.minimum_stock,
            Decimal("100"),
        )

    def test_maximum_cannot_be_lower_than_minimum(self):

        policy = StockPolicy(
            policy_level="FACILITY",
            organization=self.organization,
            facility=self.facility,
            medicine=self.medicine,
            minimum_stock=Decimal("500"),
            maximum_stock=Decimal("100"),
        )

        with self.assertRaises(ValidationError):
            policy.full_clean()

    def test_facility_must_belong_to_organization(self):

        another_org_type = OrganizationUnitType.objects.create(
            code="OTHER-ORG-TYPE",
            name="Other Organization Type",
            level=1,
        )

        another_org = Organization.objects.create(
            code="OTHER-ORG",
            name="Other Organization",
            organization_type=another_org_type,
        )

        policy = StockPolicy(
            policy_level="FACILITY",
            organization=another_org,
            facility=self.facility,
            medicine=self.medicine,
            minimum_stock=Decimal("10"),
            maximum_stock=Decimal("100"),
        )

        with self.assertRaises(ValidationError):
            policy.full_clean()

    def test_organization_policy_cannot_have_facility(self):

        policy = StockPolicy(
            policy_level="ORGANIZATION",
            organization=self.organization,
            facility=self.facility,
            medicine=self.medicine,
            minimum_stock=Decimal("10"),
            maximum_stock=Decimal("100"),
        )

        with self.assertRaises(ValidationError):
            policy.full_clean()


# ==========================================================
# STOCK POLICY EVALUATION TESTS
# ==========================================================

class StockPolicyEvaluationTests(TestCase):

    def setUp(self):

        # --------------------------------------------------
        # Organization Type
        # --------------------------------------------------

        self.organization_type = OrganizationUnitType.objects.create(
            code="EVAL-ORG-TYPE",
            name="Evaluation Organization Type",
            level=1,
        )

        # --------------------------------------------------
        # Organization
        # --------------------------------------------------

        self.organization = Organization.objects.create(
            code="EVAL-ORG",
            name="Evaluation Organization",
            organization_type=self.organization_type,
        )

        # --------------------------------------------------
        # Facility Type
        # --------------------------------------------------

        self.facility_type = FacilityType.objects.create(
            code="EVAL-HOSPITAL",
            name="Evaluation Hospital",
        )

        # --------------------------------------------------
        # Facility
        # --------------------------------------------------

        self.facility = Facility.objects.create(
            code="EVAL-FAC",
            name="Evaluation Facility",
            organization=self.organization,
            facility_type=self.facility_type,
        )

        # --------------------------------------------------
        # Warehouse
        # --------------------------------------------------

        self.warehouse = Warehouse.objects.create(
            code="EVAL-WH",
            name="Evaluation Warehouse",
            warehouse_type=WarehouseType.CENTRAL,
            organization=self.organization,
            facility=self.facility,
        )

        # --------------------------------------------------
        # Storage Zone
        # --------------------------------------------------

        self.storage_zone = StorageZone.objects.create(
            warehouse=self.warehouse,
            code="EVAL-ZONE",
            name="Evaluation Storage Zone",
            storage_type=StorageType.AMBIENT,
        )

        # --------------------------------------------------
        # Storage Location
        # --------------------------------------------------

        self.storage_location = StorageLocation.objects.create(
            zone=self.storage_zone,
            code="EVAL-LOC",
            name="Evaluation Storage Location",
        )

        # --------------------------------------------------
        # Dosage Form
        # --------------------------------------------------

        self.dosage_form = DosageForm.objects.create(
            code="TABLET",
            name="Tablet",
        )

        # --------------------------------------------------
        # Medicine
        # --------------------------------------------------

        self.medicine = Medicine.objects.create(
            code="EVAL-MED",
            generic_name="Evaluation Medicine",
            dosage_form=self.dosage_form,
        )

        # --------------------------------------------------
        # Stock Policy
        # --------------------------------------------------

        self.policy = StockPolicy.objects.create(
            policy_level="FACILITY",
            organization=self.organization,
            facility=self.facility,
            medicine=self.medicine,
            minimum_stock=Decimal("100"),
            maximum_stock=Decimal("1000"),
            safety_stock=Decimal("50"),
            lead_time_days=15,
            review_period_days=30,
            status="ACTIVE",
        )

    # ------------------------------------------------------
    # Inventory Balance Fixture
    # ------------------------------------------------------

    def create_balance(self, quantity):

        batch = StockBatch.objects.create(
            medicine=self.medicine,
            warehouse=self.warehouse,
            location=self.storage_location,
            batch_number="EVAL-BATCH-001",
            received_date=timezone.localdate(),
            expiry_date=(
                timezone.localdate() + timedelta(days=365)
            ),
        )

        return InventoryBalance.objects.create(
            batch=batch,
            quantity_on_hand=Decimal(str(quantity)),
            quantity_reserved=Decimal("0"),
        )

    # ------------------------------------------------------
    # Policy Missing
    # ------------------------------------------------------

    def test_policy_missing(self):

    # Remove the policy created by setUp().
    # This ensures that no matching policy exists in the database.
      self.policy.delete()

      result = evaluate_stock_policy(
        facility_id=self.facility.pk,
         medicine_id=self.medicine.pk,
        policy=None,
       )

      self.assertFalse(
        result["policy_configured"]
      )

      self.assertEqual(
        result["status"],
        "POLICY_MISSING",
    ) 

    # ------------------------------------------------------
    # Evaluation Without Consumption History
    # ------------------------------------------------------

    def test_policy_evaluation_without_consumption_history(self):

        self.create_balance(200)

        result = evaluate_stock_policy(
            facility_id=self.facility.pk,
            medicine_id=self.medicine.pk,
            policy=self.policy,
        )

        self.assertTrue(
            result["policy_configured"]
        )

        self.assertEqual(
            result["status"],
            "ADEQUATE",
        )

        self.assertEqual(
            Decimal(result["amc"]),
            Decimal("0"),
        )

    # ------------------------------------------------------
    # Stockout Evaluation
    # ------------------------------------------------------

    def test_stockout_evaluation(self):

        result = evaluate_stock_policy(
            facility_id=self.facility.pk,
            medicine_id=self.medicine.pk,
            policy=self.policy,
        )

        self.assertEqual(
            result["status"],
            "STOCKOUT",
        )
