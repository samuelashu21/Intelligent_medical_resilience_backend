from django.urls import include, path

urlpatterns = [
    path(
        "",
        include("apps.logistics.shipment_urls"),
    ),
]