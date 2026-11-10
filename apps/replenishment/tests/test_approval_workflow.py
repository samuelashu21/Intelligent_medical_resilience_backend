from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import (
    User,
    Role,
    UserRole,
    AccessPermission,
    RolePermission,
)

from apps.organizations.models import (
    Organization,
    OrganizationUnitType,
)

from apps.facilities.models import Facility
from apps.medicines.models import Medicine

from apps.replenishment.models import (
    ApprovalDecision,
    ApprovalWorkflow,
    ApprovalWorkflowStage,
    ReplenishmentApproval,
    ReplenishmentRequest,
)

from apps.replenishment.services import (
    create_replenishment_request,
)

from apps.replenishment.services import (
    submit_replenishment_request,
)

from apps.replenishment.approval_services import (
    decide_approval_stage,
)


class ApprovalWorkflowTests(TestCase):

    def setUp(self):

        self.national_type = OrganizationUnitType.objects.create(
            code="NATIONAL",
            name="National",
        )

        self.district_type = OrganizationUnitType.objects.create(
            code="DISTRICT",
            name="District",
        )

        self.national = Organization.objects.create(
            code="TEST-NATIONAL",
            name="Test National",
            organization_type=self.national_type,
        )

        self.district = Organization.objects.create(
            code="TEST-DISTRICT",
            name="Test District",
            organization_type=self.district_type,
            parent=self.national,
        )

        self.facility = Facility.objects.create(
            code="APPROVAL-FAC",
            name="Approval Facility",
            organization=self.district,
        )

        self.medicine = Medicine.objects.create(
            code="APPROVAL-MED",
            generic_name="Approval Test Medicine",
            dosage_form="TABLET",
        )

        self.requester = User.objects.create_user(
            email="approval.requester@example.test",
            username="approval_requester",
            password="SecurePassword123!",
        )

        self.approver = User.objects.create_user(
            email="approval.approver@example.test",
            username="approval_approver",
            password="SecurePassword123!",
        )

        self.permission = AccessPermission.objects.create(
            code="replenishment.approve",
            name="Approve Replenishment",
            module="replenishment",
        )

        self.role = Role.objects.create(
            code="DISTRICT_APPROVER",
            name="District Approver",
        )

        RolePermission.objects.create(
            role=self.role,
            permission=self.permission,
        )

        UserRole.objects.create(
            user=self.approver,
            role=self.role,
            organization=self.district,
            is_active=True,
        )

        self.workflow = ApprovalWorkflow.objects.create(
            name="District Approval",
            organization=self.district,
            created_by=self.requester,
        )

        self.stage = ApprovalWorkflowStage.objects.create(
            workflow=self.workflow,
            sequence=1,
            name="District Review",
            organization_type_code="DISTRICT",
            required_role_code="DISTRICT_APPROVER",
            required_permission_code="replenishment.approve",
            minimum_priority="LOW",
            allow_revision=True,
            allow_partial_approval=True,
            is_final_stage=True,
        )

    def create_submitted_request(self, priority="NORMAL"):

         request = create_replenishment_request(
            facility_id=self.facility.pk,
            requested_by=self.requester,
            justification="The facility requires additional stock.",
            priority=priority,
            items=[
                {
                    "medicine_id": self.medicine.pk,
                    "requested_quantity": "500",
                    "recommended_quantity": "450",
                    "unit_code": "TABLET",
                }
            ],
        )

         submit_replenishment_request(
            request.pk,
            self.requester,
        )

         request.refresh_from_db()

         return request
      

    def test_approval_stage_is_created_on_submission(self):

        request = self.create_submitted_request()

        approval = request.approval_stages.get()

        self.assertEqual(
            approval.organization,
            self.district,
        )

        self.assertEqual(
            approval.status,
            ReplenishmentApproval.Status.PENDING,
        )

    def test_district_approver_can_approve(self):

        request = self.create_submitted_request()

        approval = request.approval_stages.get()

        result = decide_approval_stage(
            approval_id=approval.pk,
            user=self.approver,
            decision=ApprovalDecision.Decision.APPROVED,
            comments="District approval completed.",
        )

        self.assertEqual(
            result.status,
            ReplenishmentApproval.Status.APPROVED,
        )

        request.refresh_from_db()

        self.assertEqual(
            request.status,
            ReplenishmentRequest.Status.APPROVED,
        )

    def test_requester_cannot_approve(self):

        request = self.create_submitted_request()

        approval = request.approval_stages.get()

        with self.assertRaises(ValidationError):

            decide_approval_stage(
                approval_id=approval.pk,
                user=self.requester,
                decision=ApprovalDecision.Decision.APPROVED,
                comments="Attempted self approval.",
            )

    def test_rejection_updates_request(self):

        request = self.create_submitted_request()

        approval = request.approval_stages.get()

        decide_approval_stage(
            approval_id=approval.pk,
            user=self.approver,
            decision=ApprovalDecision.Decision.REJECTED,
            comments="Insufficient justification.",
        )

        request.refresh_from_db()

        self.assertEqual(
            request.status,
            ReplenishmentRequest.Status.REJECTED,
        )

    def test_decision_history_is_created(self):

        request = self.create_submitted_request()

        approval = request.approval_stages.get()

        decide_approval_stage(
            approval_id=approval.pk,
            user=self.approver,
            decision=ApprovalDecision.Decision.APPROVED,
            comments="Approved after review.",
        )

        self.assertEqual(
            approval.decisions.count(),
            1,
        )

    def test_non_authorized_user_cannot_approve(self):

        request = self.create_submitted_request()

        approval = request.approval_stages.get()

        another_user = User.objects.create_user(
            email="unauthorized@example.test",
            username="unauthorized",
            password="SecurePassword123!",
        )

        with self.assertRaises(ValidationError):

            decide_approval_stage(
                approval_id=approval.pk,
                user=another_user,
                decision=ApprovalDecision.Decision.APPROVED,
                comments="Unauthorized approval.",
            )

    def test_multiple_approval_stages_are_created(self):

         regional_type = OrganizationUnitType.objects.create(
            code="REGION",
            name="Region",
        )

         regional = Organization.objects.create(
            code="TEST-REGION",
            name="Test Region",
            organization_type=regional_type,
            parent=self.national,
        )

         self.district.parent = regional
         self.district.save()

         ApprovalWorkflowStage.objects.create(
            workflow=self.workflow,
            sequence=2,
            name="Regional Review",
            organization_type_code="REGION",
            required_role_code="REGIONAL_APPROVER",
            required_permission_code="replenishment.approve",
            minimum_priority="HIGH",
            allow_revision=True,
            allow_partial_approval=True,
            is_final_stage=True,
        )

         request = self.create_submitted_request(
          priority="HIGH"
          )

         approvals = list(
            request.approval_stages.order_by(
                "workflow_stage__sequence"
            )
        )

         self.assertEqual(len(approvals), 2)

         self.assertEqual(
            approvals[0].organization,
            self.district,
        )

         self.assertEqual(
            approvals[1].organization,
            regional,
        )        