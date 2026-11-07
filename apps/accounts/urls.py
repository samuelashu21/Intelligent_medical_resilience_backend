from django.urls import path

from apps.accounts.views import (
    LoginView,
    RefreshView,
    LogoutView,
    CurrentUserView,
    PasswordChangeView,
    RBACTestView,
)

app_name = "accounts"

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