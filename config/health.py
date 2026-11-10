from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):

    return JsonResponse(
        {
            "success": True,
            "application": "MediResilience AI",
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0",
        }
    )


@require_GET
def readiness_check(request):

    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        checks["database"] = "connected"

    except Exception:
        checks["database"] = "disconnected"

    healthy = all(value == "connected" for value in checks.values())

    return JsonResponse(
        {
            "success": healthy,
            "application": "MediResilience AI",
            "status": "ready" if healthy else "not_ready",
            "checks": checks,
            "timestamp": timezone.now().isoformat(),
        },
        status=200 if healthy else 503,
    )
