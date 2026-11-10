from django.urls import include, path

urlpatterns = [
    path(
        "recommendations/",
        include("apps.redistribution.recommendation_urls"),
    ),
    path(
        "optimization/",
        include("apps.redistribution.optimization_urls"),
    ),
]
