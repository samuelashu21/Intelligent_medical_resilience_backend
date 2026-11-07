from django.urls import path, include

from config.health import health_check, readiness_check


urlpatterns = [

    path("health/", health_check),

    path("ready/", readiness_check),

    path(
        "accounts/",
        include("apps.accounts.urls"),
    ),
]