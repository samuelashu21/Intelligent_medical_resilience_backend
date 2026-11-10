from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "actor",
        "category",
        "action",
        "target_type",
        "target_id",
        "organization",
        "facility",
    ]

    list_filter = [
        "category",
        "action",
        "created_at",
    ]

    search_fields = [
        "actor__email",
        "action",
        "target_type",
        "target_id",
        "description",
    ]

    readonly_fields = [
        "id",
        "actor",
        "category",
        "action",
        "target_type",
        "target_id",
        "description",
        "organization",
        "facility",
        "changes",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
