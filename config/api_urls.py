from django.urls import path, include

from config.health import health_check, readiness_check


urlpatterns = [
    path("health/", health_check),
    path("ready/", readiness_check),
    
    path("accounts/", include("apps.accounts.urls")),
    path("organizations/", include("apps.organizations.urls")),
    path("facilities/", include("apps.facilities.urls")),
    path("audit/", include("apps.audit.urls")),
    path("medicines/", include("apps.medicines.urls")),
    path("suppliers/", include("apps.suppliers.urls")),
    path("warehouses/", include("apps.warehouses.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("consumption/", include("apps.consumption.urls")),
    path("replenishment/", include("apps.replenishment.urls")),
    path("replenishment/approval/", include("apps.replenishment.approval_urls")),
    path("procurement/", include("apps.procurement.urls")),
]