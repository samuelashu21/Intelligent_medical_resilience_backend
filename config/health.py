
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):

    database_status = "connected"

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    except Exception:
        database_status = "disconnected"

    overall_status = (
        "healthy"
        if database_status == "connected"
        else "degraded"
    )

    response_status = (
        200
        if database_status == "connected"
        else 503
    )

    return JsonResponse(
        {
            "success": database_status == "connected",
            "application": "MediResilience AI",
            "status": overall_status,
            "database": database_status,
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0",
        },
        status=response_status,
    )
