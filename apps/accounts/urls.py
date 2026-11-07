from django.urls import path

from apps.accounts.views import RBACTestView


urlpatterns = [
    path(
        "rbac-test/",
        RBACTestView.as_view(),
        name="rbac-test",
    ),
]