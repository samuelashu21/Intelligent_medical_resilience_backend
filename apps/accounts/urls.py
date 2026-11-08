
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    LoginView,
    RefreshView,
    LogoutView,
    CurrentUserView,
    PasswordChangeView,
    RBACTestView,
)
from apps.accounts.management_views import AdministrativeUserViewSet
from apps.accounts.role_assignment_views import UserRoleAssignmentViewSet

app_name = "accounts"

# Existing authentication and RBAC routes
urlpatterns = [
    # Authentication
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),

    # User account
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path(
        "auth/change-password/",
        PasswordChangeView.as_view(),
        name="change-password",
    ),

    # Phase 7 RBAC verification
    path("rbac-test/", RBACTestView.as_view(), name="rbac-test"),
]

# Administrative API routes
router = DefaultRouter()

router.register(
    "users",
    AdministrativeUserViewSet,
    basename="administrative-user",
)

router.register(
    "role-assignments",
    UserRoleAssignmentViewSet,
    basename="role-assignment",
)

# Append router-generated routes without replacing existing routes
urlpatterns += router.urls
 