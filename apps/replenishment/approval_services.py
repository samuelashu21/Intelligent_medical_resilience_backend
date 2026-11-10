from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Organization
from apps.accounts.services import user_has_permission
from apps.accounts.models import UserRole

from apps.replenishment.models import (
    ApprovalDecision,
    ApprovalWorkflow,
    ReplenishmentApproval,
    ReplenishmentRequest,
)

from apps.audit.models import AuditEvent

PRIORITY_RANK = {
    "LOW": 1,
    "NORMAL": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def get_organization_ancestors(organization):
    """
    Include the current organization and its ancestors.
    """
    result = [organization]

    if hasattr(organization, "get_ancestors"):
        result.extend(organization.get_ancestors())

    return result


def find_organization_for_stage(
    facility_organization,
    organization_type_code,
):
    """
    Find the nearest matching organization in the hierarchy.
    """
    organizations = get_organization_ancestors(facility_organization)

    for organization in organizations:
        organization_type = getattr(
            organization,
            "organization_type",
            None,
        )

        if (
            organization_type
            and organization_type.code.upper() == organization_type_code.upper()
        ):
            return organization

    raise ValidationError(
        f"No organization with type "
        f"{organization_type_code} exists in the facility hierarchy."
    )


def get_active_approval_workflow(organization):
    workflow = (
        ApprovalWorkflow.objects.filter(
            organization=organization,
            is_active=True,
        )
        .prefetch_related("stages")
        .first()
    )

    if not workflow:
        raise ValidationError(
            "No active approval workflow is configured " "for this organization."
        )

    if not workflow.stages.exists():
        raise ValidationError("The approval workflow has no stages.")

    return workflow


@transaction.atomic
def initialize_approval_workflow(request):
    request = ReplenishmentRequest.objects.select_for_update().get(pk=request.pk)

    if request.status != ReplenishmentRequest.Status.SUBMITTED:
        raise ValidationError("Only submitted requests can enter approval routing.")

    workflow = get_active_approval_workflow(request.organization)

    stages = list(workflow.stages.filter(sequence__gt=0).order_by("sequence"))

    if not stages:
        raise ValidationError("The workflow has no valid approval stages.")

    previous_sequence = 0

    existing_cycles = request.approval_stages.values_list(
        "cycle_number",
        flat=True,
    )

    cycle_number = max(existing_cycles, default=0) + 1

    approvals = []

    for stage in stages:

        if stage.sequence <= previous_sequence:
            raise ValidationError("Approval sequences must be increasing.")

        previous_sequence = stage.sequence

        if PRIORITY_RANK[request.priority] < PRIORITY_RANK[stage.minimum_priority]:
            continue

        target_organization = find_organization_for_stage(
            request.organization,
            stage.organization_type_code,
        )

        approval = ReplenishmentApproval(
            request=request,
            workflow_stage=stage,
            organization=target_organization,
            cycle_number=cycle_number,
            due_at=timezone.now() + timedelta(days=2),
        )

        approval.full_clean()
        approvals.append(approval)

    if not approvals:
        raise ValidationError("No approval stages apply to this request priority.")

    ReplenishmentApproval.objects.bulk_create(approvals)

    return request.approval_stages.filter(cycle_number=cycle_number).order_by(
        "workflow_stage__sequence"
    )


@transaction.atomic
def submit_replenishment_request(request):
    """
    Submit a replenishment request or resubmit a revised request.

    A revision-requested request can only be resubmitted
    after its previous approval cycle has no pending approvals.
    """

    request = ReplenishmentRequest.objects.select_for_update().get(pk=request.pk)

    allowed_statuses = [
        ReplenishmentRequest.Status.DRAFT,
        ReplenishmentRequest.Status.REVISION_REQUESTED,
    ]

    if request.status not in allowed_statuses:
        raise ValidationError(
            "Only draft or revision-requested requests " "can be submitted."
        )

    if request.status == ReplenishmentRequest.Status.REVISION_REQUESTED:

        latest_cycle = (
            request.approval_stages.order_by("-cycle_number")
            .values_list(
                "cycle_number",
                flat=True,
            )
            .first()
        )

        unfinished = request.approval_stages.filter(
            cycle_number=latest_cycle,
            status=ReplenishmentApproval.Status.PENDING,
        ).exists()

        if unfinished:
            raise ValidationError("The previous approval cycle is not complete.")

    request.status = ReplenishmentRequest.Status.SUBMITTED
    request.submitted_at = timezone.now()

    request.save(
        update_fields=[
            "status",
            "submitted_at",
            "updated_at",
        ]
    )

    initialize_approval_workflow(request)


def get_current_approval(request):

    latest_cycle = (
        request.approval_stages.order_by("-cycle_number")
        .values_list(
            "cycle_number",
            flat=True,
        )
        .first()
    )

    if latest_cycle is None:
        return None

    return (
        request.approval_stages.filter(
            cycle_number=latest_cycle,
            status=ReplenishmentApproval.Status.PENDING,
        )
        .order_by("workflow_stage__sequence")
        .first()
    )


def user_has_approval_role(user, approval):
    """
    Verify the user's active role assignment and permission
    within the approval organization's scope.
    """
    stage = approval.workflow_stage

    if user.is_superuser:
        return True

    if not user_has_permission(
        user,
        stage.required_permission_code,
        organization=approval.organization,
    ):
        return False

    return UserRole.objects.filter(
        user=user,
        role__code=stage.required_role_code,
        role__is_active=True,
        is_active=True,
        organization=approval.organization,
    ).exists()


@transaction.atomic
def decide_approval_stage(
    *,
    approval_id,
    user,
    decision,
    comments,
):
    approval = (
        ReplenishmentApproval.objects.select_for_update()
        .select_related(
            "request",
            "workflow_stage",
            "organization",
        )
        .get(pk=approval_id)
    )

    request = ReplenishmentRequest.objects.select_for_update().get(
        pk=approval.request_id
    )

    if request.status != ReplenishmentRequest.Status.SUBMITTED:
        raise ValidationError("This request is not awaiting approval.")

    current = get_current_approval(request)

    if not current or current.pk != approval.pk:
        raise ValidationError("This approval stage is not currently actionable.")

    if approval.status != ReplenishmentApproval.Status.PENDING:
        raise ValidationError("This approval stage has already been completed.")

    if request.requested_by_id == user.pk:
        raise ValidationError("The requester cannot approve their own request.")

    if not user_has_approval_role(user, approval):
        raise ValidationError(
            "You do not have the required role and permission "
            "for this approval stage."
        )

    if not comments or not comments.strip():
        raise ValidationError("Comments are required for approval decisions.")

    allowed = [
        ApprovalDecision.Decision.APPROVED,
        ApprovalDecision.Decision.REJECTED,
        ApprovalDecision.Decision.REVISION_REQUESTED,
    ]

    if decision not in allowed:
        raise ValidationError("Unsupported approval decision.")

    if (
        decision == ApprovalDecision.Decision.REVISION_REQUESTED
        and not approval.workflow_stage.allow_revision
    ):
        raise ValidationError("This stage does not allow revision requests.")

    if decision == ApprovalDecision.Decision.REJECTED and not comments.strip():
        raise ValidationError("A rejection reason is required.")

    request.approval_stages.filter(
        cycle_number=approval.cycle_number,
        status=ReplenishmentApproval.Status.PENDING,
    ).exclude(pk=approval.pk).update(
        status=ReplenishmentApproval.Status.SKIPPED,
        completed_at=timezone.now(),
    )

    if decision == ApprovalDecision.Decision.APPROVED:
        approval.status = ReplenishmentApproval.Status.APPROVED

    elif decision == ApprovalDecision.Decision.REJECTED:
        approval.status = ReplenishmentApproval.Status.REJECTED

    else:
        approval.status = ReplenishmentApproval.Status.REVISION_REQUESTED

    approval.decided_by = user
    approval.completed_at = timezone.now()

    approval.save(
        update_fields=[
            "status",
            "decided_by",
            "completed_at",
        ]
    )

    approval_decision = ApprovalDecision.objects.create(
        approval=approval,
        decided_by=user,
        decision=decision,
        comments=comments.strip(),
    )

    AuditEvent.objects.create(
        actor=user,
        category="SYSTEM",
        action=f"REPLENISHMENT_{decision}",
        target_type="ReplenishmentApproval",
        target_id=str(approval.pk),
        description=(
            f"{decision} at approval stage "
            f"{approval.workflow_stage.name} "
            f"for request {request.request_number}."
        ),
        organization=approval.organization,
        facility=request.facility,
        changes={
            "previous_status": ReplenishmentApproval.Status.PENDING,
            "new_status": approval.status,
        },
        metadata={
            "request_id": str(request.pk),
            "request_number": request.request_number,
            "workflow_stage_id": str(approval.workflow_stage_id),
            "decision_id": str(approval_decision.pk),
        },
    )

    if decision == ApprovalDecision.Decision.REJECTED:
        request.status = ReplenishmentRequest.Status.REJECTED
        request.rejected_by = user
        request.rejected_at = timezone.now()
        request.rejection_reason = comments.strip()

        request.save(
            update_fields=[
                "status",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
                "updated_at",
            ]
        )

    elif decision == ApprovalDecision.Decision.REVISION_REQUESTED:
        request.status = ReplenishmentRequest.Status.REVISION_REQUESTED

        request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    else:
        remaining = request.approval_stages.filter(
            cycle_number=approval.cycle_number,
            status=ReplenishmentApproval.Status.PENDING,
        ).exists()

        if not remaining:
            request.status = ReplenishmentRequest.Status.APPROVED
            request.approved_by = user
            request.approved_at = timezone.now()

            request.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                    "updated_at",
                ]
            )

    return approval
