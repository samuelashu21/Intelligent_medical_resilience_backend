from django.core.exceptions import ValidationError
from django.db import transaction

from apps.organizations.models import Organization

 
@transaction.atomic
def create_organization(
    *,
    name,
    code,
    organization_type,
    parent=None,
    **extra_fields,
):
    organization = Organization(
        name=name,
        code=code,
        organization_type=organization_type,
        parent=parent,
        **extra_fields,
    )

    organization.full_clean()
    organization.save()

    return organization


def get_organization_descendant_ids(organization):
    """
    Return the selected organization and all its descendants.

    This implementation uses iterative queries and is suitable
    for the initial platform. We can optimize large hierarchies
    with recursive SQL or a tree representation later.
    """

    result = {organization.id}
    pending = [organization.id]

    while pending:
        children = list(
            Organization.objects.filter(
                parent_id__in=pending
            ).values_list("id", flat=True)
        )

        new_ids = set(children) - result

        if not new_ids:
            break

        result.update(new_ids)
        pending = list(new_ids)

    return result


def validate_organization_parent_change(organization, new_parent):
    """
    Validate that a parent change cannot create a circular hierarchy.
    """

    if new_parent is None:
        return
 
    if organization.pk == new_parent.pk:
        raise ValidationError("An organization cannot be its own parent.")

    descendants = get_organization_descendant_ids(organization)

    if new_parent.pk in descendants:
        raise ValidationError(
            "An organization cannot be moved beneath one of its descendants."
        ) 