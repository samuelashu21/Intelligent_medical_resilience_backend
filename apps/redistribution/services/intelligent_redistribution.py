from django.db import transaction

from config.common.redistribution_client import (
    optimize_redistribution,
)

from apps.redistribution.models import (
    # Map these imports to the actual models in your project.
    RedistributionRecommendation,
)


class IntelligentRedistributionError(Exception):
    pass


def generate_intelligent_recommendations(
    *,
    user,
    payload,
):
    """
    payload must already have been built from authoritative
    Django inventory, batches, policies, routes and risk records.

    Facility authorization and organization scoping must be
    applied before this function is called.
    """

    result = optimize_redistribution(payload)

    if result["solver_status"] not in {
        "OPTIMAL",
        "FEASIBLE",
    }:
        raise IntelligentRedistributionError(
            "No feasible redistribution plan was found."
        )

    # Persist recommendations using the existing Phase 25 model.
    # The field mapping below must be adapted to its real schema.
    with transaction.atomic():

        saved = []

        for item in result["recommendations"]:

            recommendation = (
                RedistributionRecommendation.objects.create(
                    # Map the existing model's actual foreign keys.
                    created_by=user,

                    # The following fields are illustrative mapping
                    # targets; replace them with your actual fields.
                    recommended_quantity=(
                        item["recommended_quantity"]
                    ),

                    status="PROPOSED",
                )
            )

            saved.append(recommendation)

    return {
        "solver_status": result["solver_status"],
        "recommendations_created": len(saved),
    }