from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditEventViewSet

router = DefaultRouter()

router.register(
    "",
    AuditEventViewSet,
    basename="audit-event",
)

urlpatterns = router.urls
