
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    UserRole,
    Role,
)


@transaction.atomic
def assign_role(
    user,
    role,
    assigned_by=None,
):

    if not user.is_active:
        raise ValueError(
            "Cannot assign a role to an inactive user."
        )

    if not role.is_active:
        raise ValueError(
            "Cannot assign an inactive role."
        )

    assignment, created = UserRole.objects.get_or_create(
        user=user,
        role=role,
        defaults={
            "assigned_by": assigned_by,
            "is_active": True,
        },
    )

    if not created:

        assignment.is_active = True
        assignment.assigned_by = assigned_by
        assignment.valid_from = None
        assignment.valid_until = None

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
def revoke_role(user, role):

    assignment = UserRole.objects.select_for_update().filter(
        user=user,
        role=role,
        is_active=True,
    ).first()

    if assignment is None:
        return False

    assignment.is_active = False

    assignment.save(
        update_fields=["is_active"]
    )

    return True


def get_user_permissions(user):

    if not user.is_authenticated or not user.is_active:
        return set()

    if user.is_superuser:
        return {"*"}

    now = timezone.now()

    assignments = UserRole.objects.filter(
        user=user,
        is_active=True,
        role__is_active=True,
    ).filter(
        models_q_valid_from(now)
    ).filter(
        models_q_valid_until(now)
    )

    permission_codes = assignments.values_list(
        "role__permissions__code",
        flat=True,
    ).distinct()

    return {
        code
        for code in permission_codes
        if code is not None
    }


def models_q_valid_from(now):

    from django.db.models import Q

    return (
        Q(valid_from__isnull=True)
        | Q(valid_from__lte=now)
    )


def models_q_valid_until(now):

    from django.db.models import Q

    return (
        Q(valid_until__isnull=True)
        | Q(valid_until__gt=now)
    )


def user_has_permission(user, permission_code):

    if not user.is_authenticated or not user.is_active:
        return False

    if user.is_superuser:
        return True

    return permission_code in get_user_permissions(user)
