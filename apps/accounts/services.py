from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole, Role
from apps.accounts.scope_services import get_active_role_assignments
from apps.organizations.services import get_organization_descendant_ids


@transaction.atomic
def assign_role(
    *,
    user,
    role,
    assigned_by=None,
    organization=None,
    facility=None,
    valid_from=None,
    valid_until=None,
):
    if not user.is_active:
        raise ValidationError("Cannot assign a role to an inactive user.")

    if not role.is_active:
        raise ValidationError("Cannot assign an inactive role.")

    if organization and facility:
        if facility.organization_id != organization.id:
            raise ValidationError(
                "The facility must belong directly to the selected organization."
            )

    if organization and not organization.is_active:
        raise ValidationError("Cannot assign a role to an inactive organization.")

    if facility and not facility.is_active:
        raise ValidationError("Cannot assign a role to an inactive facility.")

    assignment, created = UserRole.objects.get_or_create(
        user=user,
        role=role,
        organization=organization,
        facility=facility,
        defaults={
            "assigned_by": assigned_by,
            "is_active": True,
            "valid_from": valid_from,
            "valid_until": valid_until,
        },
    )

    if not created:
        assignment.is_active = True
        assignment.assigned_by = assigned_by
        assignment.valid_from = valid_from
        assignment.valid_until = valid_until
        assignment.save(
            update_fields=[
                "is_active",
                "assigned_by",
                "valid_from",
                "valid_until",
            ]
        )

    return assignment


@transaction.atomic
def revoke_role_assignment(assignment):
    """
    Revokes one exact role assignment instance or ID.

    Returns the UserRole instance after revocation.
    Existing inactive assignments are returned unchanged.
    """

    if isinstance(assignment, UserRole):
        assignment_id = assignment.pk
    else:
        assignment_id = assignment

    assignment_obj = UserRole.objects.select_for_update().get(pk=assignment_id)

    if not assignment_obj.is_active:
        return assignment_obj

    assignment_obj.is_active = False
    assignment_obj.save(update_fields=["is_active"])

    return assignment_obj


@transaction.atomic
def revoke_role(
    user=None,
    role=None,
    *,
    assignment=None,
    assignment_id=None,
    organization=None,
    facility=None,
):
    """
    Revokes a role.

    Can be identified by:

    1. An assignment object or assignment ID.
    2. A specific scope using user, role, and optional
       organization and facility.

    Returns the revoked UserRole instance when found.
    Returns False when no matching active assignment exists.
    """

    target_id = (
        assignment_id
        if assignment_id is not None
        else (assignment.pk if isinstance(assignment, UserRole) else assignment)
    )

    if target_id is not None:
        return revoke_role_assignment(target_id)

    if user is None or role is None:
        raise ValidationError(
            "You must provide either an assignment/assignment_id "
            "or both user and role."
        )

    assignment_obj = (
        UserRole.objects.select_for_update()
        .filter(
            user=user,
            role=role,
            organization=organization,
            facility=facility,
            is_active=True,
        )
        .first()
    )

    if assignment_obj is None:
        return False

    assignment_obj.is_active = False
    assignment_obj.save(update_fields=["is_active"])

    return assignment_obj


def get_user_permissions(user):
    """
    Returns a set of active permission codes assigned to a user.
    """

    if not user.is_authenticated or not user.is_active:
        return set()

    if user.is_superuser:
        return {"*"}

    now = timezone.now()

    assignments = (
        UserRole.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True,
        )
        .filter(models_q_valid_from(now))
        .filter(models_q_valid_until(now))
    )

    permission_codes = assignments.values_list(
        "role__permissions__code",
        flat=True,
    ).distinct()

    return {code for code in permission_codes if code is not None}


def models_q_valid_from(now):
    from django.db.models import Q

    return Q(valid_from__isnull=True) | Q(valid_from__lte=now)


def models_q_valid_until(now):
    from django.db.models import Q

    return Q(valid_until__isnull=True) | Q(valid_until__gt=now)


def user_has_permission(
    user,
    permission_code,
    organization=None,
    facility=None,
):
    """
    Checks whether a user has a permission within the requested scope.
    """

    if not user.is_authenticated or not user.is_active:
        return False

    if user.is_superuser:
        return True

    assignments = get_active_role_assignments(user)

    for assignment in assignments:
        has_permission = assignment.role.permissions.filter(
            code=permission_code,
            is_active=True,
        ).exists()

        if not has_permission:
            continue

        # Globally scoped assignment can access all scopes.
        if assignment.organization_id is None and assignment.facility_id is None:
            return True

        # No resource supplied: permission exists at this scope.
        if organization is None and facility is None:
            return True

        # Facility-level resource access.
        if facility is not None:
            if assignment.facility_id == facility.id:
                return True

            # Organization-level assignment can access
            # facilities belonging to its organization descendants.
            if assignment.organization_id:
                allowed_ids = get_organization_descendant_ids(assignment.organization)

                if facility.organization_id in allowed_ids:
                    return True

        # Organization-level resource access.
        elif organization is not None:
            if assignment.organization_id:
                allowed_ids = get_organization_descendant_ids(assignment.organization)

                if organization.id in allowed_ids:
                    return True

    return False
