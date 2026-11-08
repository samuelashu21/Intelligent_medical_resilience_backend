from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from apps.medicines.models import Medicine


@transaction.atomic
def create_medicine(validated_data):
    """
    Centralized medicine creation.
    """

    medicine = Medicine(**validated_data)

    medicine.full_clean()
    medicine.save()

    return medicine


@transaction.atomic
def update_medicine(medicine, validated_data):
    """
    Update a medicine while retaining model-level validation.
    """

    for field, value in validated_data.items():
        setattr(medicine, field, value)

    medicine.full_clean()
    medicine.save()

    return medicine


def search_medicines(
    *,
    search=None,
    category=None,
    dosage_form=None,
    atc_code=None,
    essential=None,
    active=True,
):
    queryset = Medicine.objects.select_related(
        "therapeutic_category",
        "dosage_form",
        "administration_route",
        "strength_unit",
        "dispensing_unit",
    )

    if active is not None:
        queryset = queryset.filter(is_active=active)

    if search:
        from django.db.models import Q

        queryset = queryset.filter(
            Q(generic_name__icontains=search)
            | Q(brand_name__icontains=search)
            | Q(code__icontains=search)
            | Q(national_code__icontains=search)
            | Q(atc_code__icontains=search)
        )

    if category:
        queryset = queryset.filter(
            therapeutic_category__code=category
        )

    if dosage_form:
        queryset = queryset.filter(
            dosage_form__code=dosage_form
        )

    if atc_code:
        queryset = queryset.filter(
            atc_code__istartswith=atc_code
        )

    if essential is not None:
        queryset = queryset.filter(
            is_essential=essential
        )

    return queryset.order_by(
        "generic_name",
        "strength_display",
    )