from django.urls import include, path

urlpatterns = [
    path(
        "recommendations/",
        include("apps.redistribution.recommendation_urls"),
    ),
]