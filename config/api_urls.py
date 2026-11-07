from django.urls import path, include

from config.health import health_check, readiness_check


urlpatterns = [

    path("health/", health_check),

    path("ready/", readiness_check),

     path("v1/accounts/", include("apps.accounts.urls")),

    path(
        "accounts/",
        include("apps.accounts.urls"),
    ),
]