from django.contrib import admin

from apps.replenishment.models import (
    ReplenishmentRequest,
    ReplenishmentRequestLine,
    ApprovalDecision,
    ApprovalWorkflow,
    ApprovalWorkflowStage,
    ReplenishmentApproval,
)


class ReplenishmentRequestLineInline(admin.TabularInline):
    model = ReplenishmentRequestLine
    extra = 0
    can_delete = False

    readonly_fields = [
        "medicine",
        "requested_quantity",
        "recommended_quantity",
        "approved_quantity",
        "unit_code",
        "preferred_supplier",
    ]


@admin.register(ReplenishmentRequest)
class ReplenishmentRequestAdmin(admin.ModelAdmin):

    list_display = [
        "request_number",
        "facility",
        "priority",
        "source",
        "status",
        "requested_by",
        "requested_at",
    ]

    list_filter = [
        "status",
        "priority",
        "source",
        "organization",
    ]

    search_fields = [
        "request_number",
        "facility__name",
        "requested_by__email",
    ]

    readonly_fields = [
        "id",
        "request_number",
        "requested_at",
        "submitted_at",
        "approved_at",
        "rejected_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    ]

    inlines = [
        ReplenishmentRequestLineInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReplenishmentRequestLine)
class ReplenishmentRequestLineAdmin(admin.ModelAdmin):

    list_display = [
        "request",
        "medicine",
        "requested_quantity",
        "recommended_quantity",
        "approved_quantity",
        "unit_code",
    ]

    list_filter = [
        "medicine",
    ]

    search_fields = [
        "request__request_number",
        "medicine__generic_name",
        "medicine__code",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    def has_delete_permission(self, request, obj=None):
        return False


class ApprovalWorkflowStageInline(admin.TabularInline):
    model = ApprovalWorkflowStage
    extra = 1
    ordering = ["sequence"]


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "organization",
        "is_active",
        "created_by",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "organization",
    ]

    search_fields = [
        "name",
        "organization__name",
    ]

    inlines = [
        ApprovalWorkflowStageInline,
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]


@admin.register(ReplenishmentApproval)
class ReplenishmentApprovalAdmin(admin.ModelAdmin):

    list_display = [
        "request",
        "workflow_stage",
        "organization",
        "status",
        "assigned_at",
        "due_at",
        "decided_by",
    ]

    list_filter = [
        "status",
        "organization",
        "workflow_stage",
    ]

    search_fields = [
        "request__request_number",
        "organization__name",
        "workflow_stage__name",
    ]

    readonly_fields = [
        "id",
        "assigned_at",
        "completed_at",
        "decided_by",
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ApprovalDecision)
class ApprovalDecisionAdmin(admin.ModelAdmin):

    list_display = [
        "approval",
        "decided_by",
        "decision",
        "approved_at",
    ]

    list_filter = [
        "decision",
        "approved_at",
    ]

    search_fields = [
        "approval__request__request_number",
        "decided_by__email",
        "comments",
    ]

    readonly_fields = [
        "id",
        "approval",
        "decided_by",
        "decision",
        "comments",
        "approved_at",
        "metadata",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
