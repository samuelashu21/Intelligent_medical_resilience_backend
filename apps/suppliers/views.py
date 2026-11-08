from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.scope_services import (
    get_user_accessible_organization_ids,
)

from apps.suppliers.models import (
    Supplier,
    SupplierAddress,
    SupplierContact,
    SupplierContract,
    SupplierLicense,
    SupplierMedicine,
    SupplierPerformanceRecord,
    SupplierStatus,
)

from apps.suppliers.permissions import HasSupplierPermission

from apps.suppliers.serializers import (
    SupplierAddressSerializer,
    SupplierContactSerializer,
    SupplierContractSerializer,
    SupplierLicenseSerializer,
    SupplierMedicineSerializer,
    SupplierPerformanceRecordSerializer,
    SupplierSerializer,
)

from apps.suppliers.services import (
    approve_supplier,
    deactivate_supplier,
    get_supplier_performance,
    reject_supplier,
    suspend_supplier,
    verify_supplier_license,
)


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [HasSupplierPermission]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["suppliers.create"]

        elif self.action in [
            "update",
            "partial_update",
            "destroy",
            "approve",
            "reject",
            "suspend",
            "deactivate",
        ]:
            self.required_permissions = ["suppliers.update"]

        else:
            self.required_permissions = ["suppliers.view"]

        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user

        queryset = Supplier.objects.select_related(
            "country",
            "organization",
            "created_by",
            "approved_by",
        )

        if user.is_superuser:
            pass
        else:
            organization_ids = get_user_accessible_organization_ids(
                user,
                permission_code="suppliers.view",
            )

            queryset = queryset.filter(
                organization_id__in=organization_ids
            )

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        supplier_type = self.request.query_params.get("supplier_type")
        if supplier_type:
            queryset = queryset.filter(
                supplier_type=supplier_type.upper()
            )

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(registration_number__icontains=search)
                | Q(email__icontains=search)
            )

        country = self.request.query_params.get("country")
        if country:
            queryset = queryset.filter(country__code=country.upper())

        return queryset.distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data.get("organization")

        if not self.request.user.is_superuser:
            if not organization:
                raise ValidationError({
                    "organization": (
                        "An organization must be specified."
                    )
                })

            from apps.accounts.services import user_has_permission

            if not user_has_permission(
                self.request.user,
                "suppliers.create",
                organization=organization,
            ):
                raise ValidationError(
                    "You cannot register suppliers in this organization."
                )

        supplier = serializer.save(
            created_by=self.request.user,
            status=SupplierStatus.PENDING,
        )

        from apps.suppliers.services import record_supplier_audit

        record_supplier_audit(
            request=self.request,
            action="SUPPLIER_CREATED",
            supplier=supplier,
            description=f"Supplier {supplier.code} registered.",
        )

    def perform_update(self, serializer):
        supplier = self.get_object()

        old_values = {
            "name": supplier.name,
            "email": supplier.email,
            "phone": supplier.phone,
            "website": supplier.website,
        }

        supplier = serializer.save()

        new_values = {
            "name": supplier.name,
            "email": supplier.email,
            "phone": supplier.phone,
            "website": supplier.website,
        }

        from apps.suppliers.services import record_supplier_audit

        record_supplier_audit(
            request=self.request,
            action="SUPPLIER_UPDATED",
            supplier=supplier,
            description=f"Supplier {supplier.code} updated.",
            changes={
                key: {
                    "old": old_values[key],
                    "new": new_values[key],
                }
                for key in old_values
                if old_values[key] != new_values[key]
            },
        )

    def destroy(self, request, *args, **kwargs):
        raise ValidationError(
            "Suppliers cannot be deleted. Use the deactivate action."
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        supplier = self.get_object()

        try:
            supplier = approve_supplier(
                supplier_id=supplier.pk,
                approved_by=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(supplier).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        supplier = self.get_object()

        reason = request.data.get("reason", "").strip()

        if not reason:
            raise ValidationError({
                "reason": "A rejection reason is required."
            })

        try:
            supplier = reject_supplier(
                supplier_id=supplier.pk,
                rejected_by=request.user,
                reason=reason,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(supplier).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        supplier = self.get_object()

        reason = request.data.get("reason", "").strip()

        if not reason:
            raise ValidationError({
                "reason": "A suspension reason is required."
            })

        try:
            supplier = suspend_supplier(
                supplier_id=supplier.pk,
                reason=reason,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(supplier).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        supplier = self.get_object()

        reason = request.data.get("reason", "").strip()

        if not reason:
            raise ValidationError({
                "reason": "A deactivation reason is required."
            })

        try:
            supplier = deactivate_supplier(
                supplier_id=supplier.pk,
                reason=reason,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(self.get_serializer(supplier).data)

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        supplier = self.get_object()

        return Response(
            get_supplier_performance(supplier)
        )


class SupplierRelatedViewSet(viewsets.ModelViewSet):
    """
    Base class for supplier-related records.

    A related record is visible only if its supplier is visible
    through the supplier queryset.
    """

    permission_classes = [HasSupplierPermission]

    def get_permissions(self):
        if self.action == "create":
            self.required_permissions = ["suppliers.create"]

        elif self.action in [
            "update",
            "partial_update",
            "destroy",
        ]:
            self.required_permissions = ["suppliers.update"]

        else:
            self.required_permissions = ["suppliers.view"]

        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user

        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            user,
            permission_code="suppliers.view",
        )

        return queryset.filter(
            supplier__organization_id__in=organization_ids
        ).distinct()

    def perform_create(self, serializer):
        supplier = serializer.validated_data.get("supplier")

        if not supplier:
            raise ValidationError({
                "supplier": "Supplier is required."
            })

        if not self.request.user.is_superuser:
            from apps.accounts.services import user_has_permission

            if not user_has_permission(
                self.request.user,
                "suppliers.create",
                organization=supplier.organization,
            ):
                raise ValidationError(
                    "You cannot manage this supplier."
                )

        serializer.save()


class SupplierContactViewSet(SupplierRelatedViewSet):
    queryset = SupplierContact.objects.select_related("supplier")
    serializer_class = SupplierContactSerializer


class SupplierAddressViewSet(SupplierRelatedViewSet):
    queryset = SupplierAddress.objects.select_related(
        "supplier",
        "country",
    )
    serializer_class = SupplierAddressSerializer


class SupplierLicenseViewSet(SupplierRelatedViewSet):
    queryset = SupplierLicense.objects.select_related(
        "supplier",
        "verified_by",
    )
    serializer_class = SupplierLicenseSerializer

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        license_record = self.get_object()

        try:
            license_record = verify_supplier_license(
                license_id=license_record.pk,
                verified_by=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

        return Response(
            self.get_serializer(license_record).data
        )


class SupplierMedicineViewSet(SupplierRelatedViewSet):
    queryset = SupplierMedicine.objects.select_related(
        "supplier",
        "medicine",
        "presentation",
    )
    serializer_class = SupplierMedicineSerializer


class SupplierContractViewSet(SupplierRelatedViewSet):
    queryset = SupplierContract.objects.select_related(
        "supplier",
        "created_by",
    )
    serializer_class = SupplierContractSerializer


class SupplierPerformanceViewSet(
    viewsets.ReadOnlyModelViewSet
):
    permission_classes = [HasSupplierPermission]
    required_permissions = ["suppliers.view"]

    queryset = SupplierPerformanceRecord.objects.select_related(
        "supplier",
        "contract",
    )

    serializer_class = SupplierPerformanceRecordSerializer

    def get_queryset(self):
        user = self.request.user

        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset

        organization_ids = get_user_accessible_organization_ids(
            user,
            permission_code="suppliers.view",
        )

        return queryset.filter(
            supplier__organization_id__in=organization_ids
        )