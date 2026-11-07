from django.utils import timezone
from apps.accounts.models import UserRole
from apps.organizations.services import get_organization_descendant_ids


def get_active_role_assignments(user):
    """
    Return role assignments that are currently valid.
    """
    now = timezone.now()

    return UserRole.objects.filter(
        user=user,
        is_active=True,
        role__is_active=True,
    ).filter(
        models_q_valid_from(now)
    ).filter(
        models_q_valid_until(now)
    ).select_related(
        "role",
        "organization",
        "facility",
    )


def models_q_valid_from(now):
    from django.db.models import Q
    return Q(valid_from__isnull=True) | Q(valid_from__lte=now)


def models_q_valid_until(now):
    from django.db.models import Q
    return Q(valid_until__isnull=True) | Q(valid_until__gt=now)


def get_user_accessible_organization_ids(
    user,
    permission_code=None,
):
    """
    Return organizations accessible through active role assignments.

    Global role assignment grants access to all active organizations.
    Organization scope includes descendants.
    Facility scope does not grant organization-wide access.
    """
    from apps.organizations.models import Organization

    if not user.is_authenticated or not user.is_active:
        return set()

    if user.is_superuser:
        return set(
            Organization.objects.filter(
                is_active=True
            ).values_list("id", flat=True)
        )

    assignments = get_active_role_assignments(user)
    accessible = set()

    for assignment in assignments:
        if permission_code and not assignment.role.permissions.filter(
            code=permission_code,
            is_active=True,
        ).exists():
            continue

        if (
            assignment.organization_id is None
            and assignment.facility_id is None
        ):
            return set(
                Organization.objects.filter(
                    is_active=True
                ).values_list("id", flat=True)
            )

        if assignment.organization_id:
            accessible.update(
                get_organization_descendant_ids(
                    assignment.organization
                )
            )

    return accessible


def get_user_accessible_facility_ids(
    user,
    permission_code=None,
):
    """
    Return facility IDs visible to the user through active role assignments.
    """
    from apps.facilities.models import Facility

    if not user.is_authenticated or not user.is_active:
        return set()

    if user.is_superuser:
        return set(
            Facility.objects.filter(
                is_active=True
            ).values_list("id", flat=True)
        )

    assignments = get_active_role_assignments(user)
    accessible = set()

    for assignment in assignments:
        if permission_code and not assignment.role.permissions.filter(
            code=permission_code,
            is_active=True,
        ).exists():
            continue

        if (
            assignment.organization_id is None
            and assignment.facility_id is None
        ):
            return set(
                Facility.objects.filter(
                    is_active=True
                ).values_list("id", flat=True)
            )

        if assignment.facility_id:
            accessible.add(assignment.facility_id)

        if assignment.organization_id:
            organization_ids = get_organization_descendant_ids(
                assignment.organization
            )

            accessible.update(
                Facility.objects.filter(
                    organization_id__in=organization_ids,
                    is_active=True,
                ).values_list("id", flat=True)
            )

    return accessible


def user_can_access_organization(user, organization, permission_code=None):
    """
    Check whether a user can access an organization.
    """
    if not user.is_authenticated or not user.is_active:
        return False

    if not organization.is_active:
        return False

    if user.is_superuser:
        return True

    assignments = get_active_role_assignments(user)

    for assignment in assignments:
        if permission_code and not assignment.role.permissions.filter(
            code=permission_code,
            is_active=True,
        ).exists():
            continue

        if (
            assignment.organization_id is None
            and assignment.facility_id is None
        ):
            return True

        if assignment.organization_id:
            allowed_ids = get_organization_descendant_ids(
                assignment.organization
            )

            if organization.id in allowed_ids:
                return True

    return False


def user_can_access_facility(user, facility, permission_code=None):
    """
    Check whether a user can access a specific facility.
    """
    if not user.is_authenticated or not user.is_active:
        return False

    if not facility.is_active:
        return False

    if user.is_superuser:
        return True

    assignments = get_active_role_assignments(user)

    for assignment in assignments:
        if permission_code and not assignment.role.permissions.filter(
            code=permission_code,
            is_active=True,
        ).exists():
            continue

        if (
            assignment.organization_id is None
            and assignment.facility_id is None
        ):
            return True

        if assignment.facility_id == facility.id:
            return True

        if assignment.organization_id:
            allowed_ids = get_organization_descendant_ids(
                assignment.organization
            )

            if facility.organization_id in allowed_ids:
                return True

    return False