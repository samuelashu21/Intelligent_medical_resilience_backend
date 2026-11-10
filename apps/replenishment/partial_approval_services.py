from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.replenishment.models import (
    ReplenishmentApproval,
    ReplenishmentRequestLine,
)


@transaction.atomic
def validate_and_apply_partial_approval(
    approval,
    approved_quantities,
):
    stage = approval.workflow_stage

    if not stage.allow_partial_approval:
        raise ValidationError("Partial approval is not permitted at this stage.")

    lines = list(
        ReplenishmentRequestLine.objects.select_for_update().filter(
            request=approval.request
        )
    )

    line_map = {str(line.pk): line for line in lines}

    unknown_ids = set(approved_quantities.keys()) - set(line_map.keys())

    if unknown_ids:
        raise ValidationError("One or more line IDs do not belong to this request.")

    for line_id, raw_quantity in approved_quantities.items():
        line = line_map[line_id]
        quantity = Decimal(str(raw_quantity))

        if quantity < 0:
            raise ValidationError("Approved quantities cannot be negative.")

        if quantity > line.requested_quantity:
            raise ValidationError("Approved quantity cannot exceed requested quantity.")

        line.approved_quantity = quantity

        line.save(
            update_fields=[
                "approved_quantity",
                "updated_at",
            ]
        )

    if not any(
        line.approved_quantity is not None and line.approved_quantity > 0
        for line in lines
    ):
        raise ValidationError(
            "At least one line must have a positive approved quantity."
        )

    return lines
