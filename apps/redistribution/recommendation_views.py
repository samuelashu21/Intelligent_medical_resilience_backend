
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
)

from apps.accounts.permissions import HasSystemPermission
from apps.accounts.scope_services import (
    get_user_accessible_facility_ids,
)

from apps.audit.services import record_audit_event

from apps.redistribution.recommendation_models import (
    RedistributionRecommendation,
    RecommendationStatus,
)

from apps.redistribution.recommendation_services import (
    generate_redistribution_recommendations,
)

from apps.redistribution.recommendation_serializers import (
    RedistributionRecommendationSerializer,
    RecommendationReviewSerializer,
    GenerateRecommendationSerializer,
)


# ==========================================================
# ATOMIC RECOMMENDATION REVIEW SERVICE
# ==========================================================

@transaction.atomic
def review_recommendation_record(
    *,
    recommendation_id,
    user,
    new_status,
    reason,
):
    """
    Review a redistribution recommendation atomically.

    Uses select_for_update() to prevent concurrent reviews
    of the same recommendation.

    The recommendation update and audit event are committed
    together or rolled back together.
    """

    try:
        recommendation = (
            RedistributionRecommendation.objects
            .select_for_update()
            .select_related(
                "medicine",
                "donor_facility",
                "recipient_facility",
                "donor_organization",
                "recipient_organization",
            )
            .get(pk=recommendation_id)
        )

    except RedistributionRecommendation.DoesNotExist:
        raise NotFound(
            "Redistribution recommendation not found."
        )

    # Only pending recommendations can be reviewed.
    if recommendation.status != RecommendationStatus.PENDING:
        raise ValidationError(
            "Only pending recommendations can be reviewed."
        )

    # Check expiration while holding the database row lock.
    if (
        recommendation.expires_at
        and recommendation.expires_at <= timezone.now()
    ):
        recommendation.status = RecommendationStatus.EXPIRED

        recommendation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise ValidationError(
            "This recommendation has expired."
        )

    # Preserve the original status for audit logging.
    old_status = recommendation.status

    # Apply the review.
    recommendation.status = new_status
    recommendation.reviewed_by = user
    recommendation.reviewed_at = timezone.now()
    recommendation.review_reason = reason

    recommendation.save()

    # Record the audit event inside the same transaction.
    record_audit_event(
        actor=user,
        category="SYSTEM",
        action=f"REDISTRIBUTION_RECOMMENDATION_{new_status}",
        target_type="RedistributionRecommendation",
        target_id=str(recommendation.pk),
        description=(
            f"Recommendation {recommendation.recommendation_number} "
            f"was {new_status.lower()}."
        ),
        organization=recommendation.recipient_organization,
        changes={
            "status": {
                "old": old_status,
                "new": new_status,
            },
        },
        metadata={
            "donor_facility_id": str(
                recommendation.donor_facility_id
            ),
            "recipient_facility_id": str(
                recommendation.recipient_facility_id
            ),
            "medicine_id": str(
                recommendation.medicine_id
            ),
            "recommended_quantity": str(
                recommendation.recommended_quantity
            ),
        },
    )

    return recommendation


# ==========================================================
# REDISTRIBUTION RECOMMENDATION VIEWSET
# ==========================================================

class RedistributionRecommendationViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = RedistributionRecommendationSerializer

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def get_required_permission(self):

        if self.action == "generate":
            return "redistribution.recommendation.generate"

        if self.action in [
            "accept",
            "reject",
            "defer",
        ]:
            return "redistribution.recommendation.review"

        return "redistribution.recommendation.view"

    def get_permissions(self):

        self.required_permissions = [
            self.get_required_permission()
        ]

        return super().get_permissions()

    def get_queryset(self):

        user = self.request.user

        queryset = (
            RedistributionRecommendation.objects
            .select_related(
                "medicine",
                "donor_facility",
                "recipient_facility",
                "donor_organization",
                "recipient_organization",
                "reviewed_by",
            )
        )

        # --------------------------------------------------
        # FACILITY SCOPE FILTERING
        # --------------------------------------------------

        if not user.is_superuser:

            visible_ids = get_user_accessible_facility_ids(
                user,
                permission_code="redistribution.recommendation.view",
            )

            queryset = queryset.filter(
                donor_facility_id__in=visible_ids,
                recipient_facility_id__in=visible_ids,
            ).distinct()

        # --------------------------------------------------
        # OPTIONAL QUERY PARAMETER FILTERING
        # --------------------------------------------------

        medicine_id = self.request.query_params.get("medicine")
        priority = self.request.query_params.get("priority")
        recommendation_status = self.request.query_params.get("status")
        donor_id = self.request.query_params.get("donor")
        recipient_id = self.request.query_params.get("recipient")

        if medicine_id:
            queryset = queryset.filter(
                medicine_id=medicine_id
            )

        if priority:
            queryset = queryset.filter(
                priority=priority
            )

        if recommendation_status:
            queryset = queryset.filter(
                status=recommendation_status
            )

        if donor_id:
            queryset = queryset.filter(
                donor_facility_id=donor_id
            )

        if recipient_id:
            queryset = queryset.filter(
                recipient_facility_id=recipient_id
            )

        return queryset

    def get_serializer_class(self):

        if self.action in [
            "accept",
            "reject",
            "defer",
        ]:
            return RecommendationReviewSerializer

        if self.action == "generate":
            return GenerateRecommendationSerializer

        return RedistributionRecommendationSerializer

    # ------------------------------------------------------
    # GENERATE RECOMMENDATIONS
    # ------------------------------------------------------

    @action(detail=False, methods=["post"])
    def generate(self, request):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            recommendations = (
                generate_redistribution_recommendations(
                    user=request.user,
                    medicine_id=serializer.validated_data["medicine"],
                    amc_months=serializer.validated_data["amc_months"],
                    maximum_distance_km=(
                        serializer.validated_data.get(
                            "maximum_distance_km"
                        )
                    ),
                )
            )

        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        output = RedistributionRecommendationSerializer(
            recommendations,
            many=True,
        )

        return Response(
            {
                "generated_count": len(recommendations),
                "results": output.data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------
    # COMMON ATOMIC REVIEW HANDLER
    # ------------------------------------------------------

    def review_recommendation(
        self,
        request,
        new_status,
    ):
        """
        Validate review input and delegate the operation
        to the atomic, row-locked review service.
        """

        serializer = RecommendationReviewSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            recommendation = review_recommendation_record(
                recommendation_id=self.get_object().pk,
                user=request.user,
                new_status=new_status,
                reason=serializer.validated_data["reason"],
            )

        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            RedistributionRecommendationSerializer(
                recommendation
            ).data
        )

    # ------------------------------------------------------
    # ACCEPT RECOMMENDATION
    # ------------------------------------------------------

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):

        return self.review_recommendation(
            request,
            RecommendationStatus.ACCEPTED,
        )

    # ------------------------------------------------------
    # REJECT RECOMMENDATION
    # ------------------------------------------------------

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):

        return self.review_recommendation(
            request,
            RecommendationStatus.REJECTED,
        )

    # ------------------------------------------------------
    # DEFER RECOMMENDATION
    # ------------------------------------------------------

    @action(detail=True, methods=["post"])
    def defer(self, request, pk=None):

        return self.review_recommendation(
            request,
            RecommendationStatus.DEFERRED,
        )
