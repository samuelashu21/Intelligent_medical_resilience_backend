from django.core.exceptions import ValidationError
from django.db import transaction

from apps.facilities.models import Facility


@transaction.atomic
def create_facility(
    *,
    name,
    code,
    facility_type,
    organization,
    **extra_fields,
):
    facility = Facility(
        name=name,
        code=code,
        facility_type=facility_type,
        organization=organization,
        **extra_fields,
    )

    facility.full_clean()
    facility.save()
 
    return facility  