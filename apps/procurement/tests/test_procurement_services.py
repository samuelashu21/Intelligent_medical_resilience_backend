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

from apps.facilities.models import Facility
from apps.medicines.models import Medicine

from apps.suppliers.models import Supplier

from apps.replenishment.models import (
    ReplenishmentRequest,
    ReplenishmentRequestLine,
)

from apps.procurement.models import (
    PurchaseRequisitionStatus,
    PurchaseOrderStatus,
    QuotationStatus,
)

from apps.procurement.services import (
    create_purchase_requisition,
    submit_purchase_requisition,
    approve_purchase_requisition,
    add_supplier_quotation,
    select_supplier_quotation,
    create_purchase_order,
    submit_purchase_order_for_approval,
    approve_purchase_order,
    send_purchase_order,
)


class ProcurementServiceTests(TestCase):

    def setUp(self):

        self.unit_type = OrganizationUnitType.objects.create(
            code="PROC-DISTRICT",
            name="Procurement District",
        )

        self.organization = Organization.objects.create(
            code="PROC-ORG",
            name="Procurement Organization",
            organization_type=self.unit_type,
        )

        self.facility = Facility.objects.create(
            code="PROC-FAC",
            name="Procurement Facility",
            organization=self.organization,
        )

        self.requester = User.objects.create_user(
            email="procurement.requester@example.test",
            username="procurement_requester",
            password="SecurePassword123!",
        )

        self.approver = User.objects.create_user(
            email="procurement.approver@example.test",
            username="procurement_approver",
            password="SecurePassword123!",
        )

        self.medicine = Medicine.objects.create(
            code="PROC-MED-001",
            generic_name="Procurement Test Medicine",
            dosage_form="TABLET",
        )

        self.supplier = Supplier.objects.create(
            code="PROC-SUP-001",
            name="Approved Procurement Supplier",
            supplier_type="DISTRIBUTOR",
            status="PENDING",
        )

        # Use the supplier approval service so approval metadata
        # is set consistently with the Phase 13 model validation.
        from apps.suppliers.services import approve_supplier

        approve_supplier(
            supplier_id=self.supplier.pk,
            approved_by=self.approver,
        )

        self.replenishment = ReplenishmentRequest.objects.create(
            facility=self.facility,
            organization=self.organization,
            requested_by=self.requester,
            priority="NORMAL",
            source="MANUAL",
            status="APPROVED",
            justification="Approved medicine requirement.",
            approved_by=self.approver,
            approved_at=timezone.now(),
        )

        self.replenishment_line = ReplenishmentRequestLine.objects.create(
            request=self.replenishment,
            medicine=self.medicine,
            requested_quantity=Decimal("500"),
            recommended_quantity=Decimal("450"),
            approved_quantity=Decimal("400"),
            unit_code="TABLET",
        )

    def create_requisition(self):

        return create_purchase_requisition(
            replenishment_request_id=self.replenishment.pk,
            user=self.requester,
        )

    def test_create_purchase_requisition(self):

        requisition = self.create_requisition()

        self.assertEqual(
            requisition.status,
            PurchaseRequisitionStatus.DRAFT,
        )

        self.assertEqual(
            requisition.items.count(),
            1,
        )

        self.assertEqual(
            requisition.items.first().quantity,
            Decimal("400"),
        )

    def test_only_approved_request_can_be_converted(self):

        self.replenishment.status = "SUBMITTED"
        self.replenishment.save()

        with self.assertRaises(ValidationError):
            self.create_requisition()

    def test_requisition_submission_and_approval(self):

        requisition = self.create_requisition()

        submit_purchase_requisition(
            requisition.pk,
            self.requester,
        )

        requisition.refresh_from_db()

        self.assertEqual(
            requisition.status,
            PurchaseRequisitionStatus.SUBMITTED,
        )

        approve_purchase_requisition(
            requisition.pk,
            self.approver,
        )

        requisition.refresh_from_db()

        self.assertEqual(
            requisition.status,
            PurchaseRequisitionStatus.APPROVED,
        )

    def test_creator_cannot_approve_requisition(self):

        requisition = self.create_requisition()

        submit_purchase_requisition(
            requisition.pk,
            self.requester,
        )

        with self.assertRaises(ValidationError):
            approve_purchase_requisition(
                requisition.pk,
                self.requester,
            )

    def create_selected_quotation(self):

        requisition = self.create_requisition()

        submit_purchase_requisition(
            requisition.pk,
            self.requester,
        )

        approve_purchase_requisition(
            requisition.pk,
            self.approver,
        )

        line = requisition.items.get()

        quotation = add_supplier_quotation(
            requisition_id=requisition.pk,
            supplier_id=self.supplier.pk,
            quotation_number="QUOTE-001",
            currency="USD",
            valid_until=timezone.localdate() + timedelta(days=30),
            delivery_days=14,
            submitted_by=self.requester,
            items=[
                {
                    "requisition_line_id": line.pk,
                    "quantity": "400",
                    "unit_price": "0.25",
                }
            ],
        )

        select_supplier_quotation(
            quotation_id=quotation.pk,
            user=self.approver,
            justification=(
                "Supplier has acceptable price, delivery, " "and quality performance."
            ),
        )

        return requisition, quotation

    def test_create_purchase_order(self):

        requisition, quotation = self.create_selected_quotation()

        order = create_purchase_order(
            quotation_id=quotation.pk,
            user=self.requester,
            tax_amount="5",
            shipping_amount="10",
        )

        self.assertEqual(
            order.status,
            PurchaseOrderStatus.DRAFT,
        )

        self.assertEqual(
            order.subtotal,
            Decimal("100.0000"),
        )

        self.assertEqual(
            order.total_amount,
            Decimal("115.0000"),
        )

        self.assertEqual(order.items.count(), 1)

    def test_purchase_order_approval_and_sending(self):

        requisition, quotation = self.create_selected_quotation()

        order = create_purchase_order(
            quotation_id=quotation.pk,
            user=self.requester,
        )

        submit_purchase_order_for_approval(
            order.pk,
            self.requester,
        )

        approve_purchase_order(
            order.pk,
            self.approver,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            PurchaseOrderStatus.APPROVED,
        )

        send_purchase_order(
            order.pk,
            self.approver,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            PurchaseOrderStatus.SENT,
        )

    def test_purchase_order_creator_cannot_approve(self):

        requisition, quotation = self.create_selected_quotation()

        order = create_purchase_order(
            quotation_id=quotation.pk,
            user=self.requester,
        )

        submit_purchase_order_for_approval(
            order.pk,
            self.requester,
        )

        with self.assertRaises(ValidationError):
            approve_purchase_order(
                order.pk,
                self.requester,
            )

    def test_expired_quotation_cannot_be_selected(self):

        requisition = self.create_requisition()

        submit_purchase_requisition(
            requisition.pk,
            self.requester,
        )

        approve_purchase_requisition(
            requisition.pk,
            self.approver,
        )

        line = requisition.items.get()

        quotation = add_supplier_quotation(
            requisition_id=requisition.pk,
            supplier_id=self.supplier.pk,
            quotation_number="QUOTE-EXPIRED",
            currency="USD",
            valid_until=timezone.localdate() - timedelta(days=1),
            delivery_days=10,
            submitted_by=self.requester,
            items=[
                {
                    "requisition_line_id": line.pk,
                    "quantity": "400",
                    "unit_price": "0.25",
                }
            ],
        )

        with self.assertRaises(ValidationError):
            select_supplier_quotation(
                quotation_id=quotation.pk,
                user=self.approver,
                justification="Supplier selection justification.",
            )
