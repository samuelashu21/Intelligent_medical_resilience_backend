
from django.urls import path

from config.health import health_check


urlpatterns = [

    path(
        "health/",
        health_check,
        name="versioned-health-check",
    ),

]
