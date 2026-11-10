from django.urls import include, path

urlpatterns = [
    path(
        "",
        include("apps.logistics.shipment_urls"),
    ),
    path(
    "",
    include("apps.logistics.receiving_urls"),
),
]