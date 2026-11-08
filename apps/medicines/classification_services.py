from django.db.models import Q
from django.utils import timezone

from apps.medicines.models import (
    ATCClassification,
    EssentialMedicineItem,
    Medicine,
    MedicineEligibilityRule,
)


def get_atc_descendants(classification):
    """
    Return a classification and all descendants.
    """

    result = [classification]

    children = ATCClassification.objects.filter(
        parent=classification,
        is_active=True,
    )

    for child in children:
        result.extend(get_atc_descendants(child))

    return result


def get_medicines_by_atc(classification):
    """
    Return medicines assigned directly to a classification
    or any of its descendants.
    """

    classifications = get_atc_descendants(classification)

    classification_ids = [
        item.id for item in classifications
    ]

    return Medicine.objects.filter(
        atc_classification_id__in=classification_ids,
        is_active=True,
    ).distinct()


def get_current_essential_medicines(country):
    """
    Retrieve medicines in the currently effective active EML.
    """

    today = timezone.localdate()

    return Medicine.objects.filter(
        essential_list_entries__is_active=True,
        essential_list_entries__essential_list__country=country,
        essential_list_entries__essential_list__is_active=True,
        essential_list_entries__essential_list__effective_from__lte=today,
    ).filter(
        Q(
            essential_list_entries__essential_list__effective_until__isnull=True
        )
        | Q(
            essential_list_entries__essential_list__effective_until__gte=today
        )
    ).distinct()


def get_medicine_eligibility(
    *,
    medicine,
    country=None,
    organization=None,
    facility=None,
    date=None,
):
    """
    Evaluate active rules for a medicine.

    More specific rules take precedence:
    facility > organization > country > global.

    If multiple rules exist at the same specificity and scope,
    a restriction takes precedence over an allowance.
    """

    date = date or timezone.localdate()

    queryset = MedicineEligibilityRule.objects.filter(
        medicine=medicine,
        is_active=True,
        effective_from__lte=date,
    ).filter(
        Q(effective_until__isnull=True)
        | Q(effective_until__gte=date)
    )

    if facility:
        queryset = queryset.filter(
            Q(facility=facility)
            | Q(facility__isnull=True, organization=organization)
            | Q(
                facility__isnull=True,
                organization__isnull=True,
                country=country,
            )
            | Q(
                facility__isnull=True,
                organization__isnull=True,
                country__isnull=True,
            )
        )

    elif organization:
        queryset = queryset.filter(
            Q(
                organization=organization,
                facility__isnull=True,
            )
            | Q(
                organization__isnull=True,
                facility__isnull=True,
                country=country,
            )
            | Q(
                organization__isnull=True,
                facility__isnull=True,
                country__isnull=True,
            )
        )

    elif country:
        queryset = queryset.filter(
            Q(
                country=country,
                organization__isnull=True,
                facility__isnull=True,
            )
            | Q(
                country__isnull=True,
                organization__isnull=True,
                facility__isnull=True,
            )
        )

    else:
        queryset = queryset.filter(
            country__isnull=True,
            organization__isnull=True,
            facility__isnull=True,
        )

    rules = list(queryset)

    if not rules:
        return {
            "allowed": True,
            "matched_rule": None,
            "reason": "No applicable restriction rule exists.",
        }

    def specificity(rule):
        if rule.facility_id:
            return 4
        if rule.organization_id:
            return 3
        if rule.country_id:
            return 2
        return 1

    highest = max(specificity(rule) for rule in rules)

    matching = [
        rule for rule in rules
        if specificity(rule) == highest
    ]

    restrictions = [
        rule for rule in matching
        if not rule.is_allowed
    ]

    selected = restrictions[0] if restrictions else matching[0]

    return {
        "allowed": selected.is_allowed,
        "matched_rule": selected,
        "reason": selected.reason,
    }