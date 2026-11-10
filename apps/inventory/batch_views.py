from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)

from apps.inventory.models import (
    BatchExpiryAlert,
    BatchLifecycleEvent,
    BatchStatus,
    StockBatch,
)

from apps.inventory.permissions import HasInventoryPermission

from apps.inventory.batch_serializers import (
    BatchExpiryAlertSerializer,
    BatchLifecycleEventSerializer,
)

from apps.inventory.batch_services import (
    dispose_batch,
    mark_batch_damaged,
    quarantine_batch,
    recall_batch,
    release_quarantined_batch,
)


def check_batch_permission(user, batch, permission_code):
    if user.is_superuser:
        return

    from apps.accounts.services import user_has_permission

    if not user_has_permission(
        user,
        permission_code,
        organization=batch.warehouse.organization,
    ):
        raise ValidationError(
            "You do not have permission to manage this batch "
            "in the selected organization."
        )


class BatchLifecycleViewSet(viewsets.GenericViewSet):
    permission_classes = [HasInventoryPermission]

    def get_queryset(self):
        queryset = StockBatch.objects.select_related(
            "medicine",
            "warehouse",
        )

        if self.request.user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            self.request.user,
            permission_code="inventory.view",
        )

        return queryset.filter(warehouse__organization_id__in=organization_ids)

    def get_batch(self):
        return self.get_object()

    def lifecycle_response(self, batch):
        return Response(
            {
                "id": str(batch.pk),
                "batch_number": batch.batch_number,
                "status": batch.status,
                "is_usable": batch.is_usable,
                "days_until_expiry": batch.days_until_expiry,
            }
        )

    @action(detail=True, methods=["post"])
    def quarantine(self, request, pk=None):
        batch = self.get_batch()

        check_batch_permission(
            request.user,
            batch,
            "inventory.adjust",
        )

        try:
            batch = quarantine_batch(
                batch_id=batch.pk,
                performed_by=request.user,
                reason=request.data.get("reason", ""),
                reference_number=request.data.get("reference_number", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return self.lifecycle_response(batch)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        batch = self.get_batch()

        check_batch_permission(
            request.user,
            batch,
            "inventory.adjust",
        )

        try:
            batch = release_quarantined_batch(
                batch_id=batch.pk,
                performed_by=request.user,
                reason=request.data.get("reason", ""),
                reference_number=request.data.get("reference_number", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return self.lifecycle_response(batch)

    @action(detail=True, methods=["post"])
    def damage(self, request, pk=None):
        batch = self.get_batch()

        check_batch_permission(
            request.user,
            batch,
            "inventory.adjust",
        )

        try:
            batch = mark_batch_damaged(
                batch_id=batch.pk,
                performed_by=request.user,
                reason=request.data.get("reason", ""),
                reference_number=request.data.get("reference_number", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return self.lifecycle_response(batch)

    @action(detail=True, methods=["post"])
    def recall(self, request, pk=None):
        batch = self.get_batch()

        check_batch_permission(
            request.user,
            batch,
            "inventory.adjust",
        )

        try:
            batch = recall_batch(
                batch_id=batch.pk,
                performed_by=request.user,
                reason=request.data.get("reason", ""),
                reference_number=request.data.get("reference_number", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return self.lifecycle_response(batch)

    @action(detail=True, methods=["post"])
    def dispose(self, request, pk=None):
        batch = self.get_batch()

        check_batch_permission(
            request.user,
            batch,
            "inventory.adjust",
        )

        try:
            batch = dispose_batch(
                batch_id=batch.pk,
                performed_by=request.user,
                reason=request.data.get("reason", ""),
                reference_number=request.data.get("reference_number", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return self.lifecycle_response(batch)


class BatchExpiryAlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BatchExpiryAlertSerializer
    permission_classes = [HasInventoryPermission]

    required_permissions = ["inventory.view"]

    queryset = BatchExpiryAlert.objects.select_related(
        "batch",
        "batch__medicine",
        "batch__warehouse",
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                self.request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                batch__warehouse__organization_id__in=organization_ids
            )

        active = self.request.query_params.get("active")

        if active in ["true", "false"]:
            queryset = queryset.filter(is_active=(active == "true"))

        level = self.request.query_params.get("level")

        if level:
            queryset = queryset.filter(alert_level=level.upper())

        return queryset


class BatchLifecycleEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BatchLifecycleEventSerializer
    permission_classes = [HasInventoryPermission]

    required_permissions = ["inventory.view"]

    queryset = BatchLifecycleEvent.objects.select_related(
        "batch",
        "performed_by",
        "batch__warehouse",
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            organization_ids = get_user_accessible_organization_ids(
                self.request.user,
                permission_code="inventory.view",
            )

            queryset = queryset.filter(
                batch__warehouse__organization_id__in=organization_ids
            )

        batch_id = self.request.query_params.get("batch")

        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        action_filter = self.request.query_params.get("action")

        if action_filter:
            queryset = queryset.filter(action=action_filter.upper())

        return queryset
