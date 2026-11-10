import logging

from django.contrib.auth import update_session_auth_hash

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.throttling import ScopedRateThrottle

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


from apps.accounts.permissions import HasSystemPermission
from apps.accounts.serializers.auth_serializers import (
    CustomTokenObtainPairSerializer,
    CurrentUserSerializer,
    PasswordChangeSerializer,
)


class LoginView(TokenObtainPairView):
    """
    Authenticate a user using email and password.
    """

    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class RefreshView(TokenRefreshView):
    """
    Exchange a refresh token for a new access token.
    Refresh rotation is configured in settings.
    """

    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    Blacklist the supplied refresh token.

    Requires an authenticated user and a valid refresh token
    belonging to that user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)

            # Verify token ownership.
            user_id = token.payload.get("user_id") or token.payload.get("sub")

            if user_id and str(user_id) != str(request.user.id):
                return Response(
                    {"detail": "Invalid refresh token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Blacklist refresh token.
            token.blacklist()

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except TokenError as exc:
            return Response(
                {"detail": (str(exc) or "Invalid or expired refresh token.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            logger = logging.getLogger("mediresilience.api")
            logger.exception("Unexpected error during logout.")

            return Response(
                {"detail": "An error occurred during logout."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CurrentUserView(generics.RetrieveAPIView):
    """
    Return the authenticated user's account, profile, roles and permissions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserSerializer

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """
    Allow an authenticated user to change their password.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        # If the serializer defines a save method, use it; otherwise update user directly.
        if hasattr(serializer, "save") and callable(getattr(serializer, "save")):
            serializer.save()
        else:
            user = request.user
            new_password = serializer.validated_data.get("new_password")
            user.set_password(new_password)
            user.save(update_fields=["password"])
            update_session_auth_hash(request, user)

        return Response(
            {"detail": ("Password changed successfully. " "Please log in again.")},
            status=status.HTTP_200_OK,
        )


class RBACTestView(APIView):
    """
    Test endpoint for verifying Role-Based Access Control (RBAC) permissions.
    """

    permission_classes = [
        IsAuthenticated,
        HasSystemPermission,
    ]

    required_permissions = ("inventory.view",)

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "Inventory permission verified.",
                "user": request.user.email,
                "permissions": list(
                    sorted(
                        request.user.role_assignments.filter(
                            is_active=True,
                            role__is_active=True,
                        ).values_list(
                            "role__code",
                            flat=True,
                        )
                    )
                ),
            }
        )
