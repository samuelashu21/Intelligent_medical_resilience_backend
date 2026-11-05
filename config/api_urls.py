from django.urls import path

from config.health import health_check, readiness_check


urlpatterns = [
    path("health/", health_check),
    path("ready/", readiness_check),
]