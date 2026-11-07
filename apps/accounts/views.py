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
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)

            # Prevent a user from blacklisting another user's token.
            if str(token["user_id"]) != str(request.user.id):
                return Response(
                    {"detail": "Invalid refresh token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token.blacklist()

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CurrentUserView(generics.RetrieveAPIView):
    """
    Return the authenticated user's account, profile, roles and permissions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserSerializer

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """
    Allow an authenticated user to change their password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        request.user.set_password(
            serializer.validated_data["new_password"]
        )

        request.user.save(update_fields=["password"])

        # Password changes invalidate existing password-derived
        # authentication sessions, but JWTs need explicit revocation.
        return Response(
            {
                "detail": (
                    "Password changed successfully. "
                    "Please log in again."
                )
            },
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