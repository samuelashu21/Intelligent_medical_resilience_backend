
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasSystemPermission


class RBACTestView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    required_permissions = (
        "inventory.view",
    )

    def get(self, request):

        return Response(
            {
                "success": True,
                "message": "Inventory permission verified.",
                "user": request.user.email,
                "permissions": list(
                    sorted(
                        request.user.role_assignments
                        .filter(
                            is_active=True,
                            role__is_active=True,
                        )
                        .values_list(
                            "role__code",
                            flat=True,
                        )
                    )
                ),
            }
        )
