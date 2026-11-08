
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User, UserProfile, UserRole
from apps.audit.models import AuditEvent


User = get_user_model()


# ============================================================
# AUTHENTICATION SERIALIZERS
# ============================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Email/password authentication with additional account checks.

    Features:
    - Email-based authentication.
    - Normalized email addresses.
    - Inactive account protection.
    - JWT access and refresh token generation.
    - Additional user information in login response.
    """

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        if not email or not password:
            raise serializers.ValidationError({
                "detail": "Email and password are required."
            })

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError({
                "detail": "Invalid email or password."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "This account is inactive."
            })

        # Generate JWT tokens using SimpleJWT.
        data = super().validate(attrs)

        # Include authenticated user information.
        data["user"] = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        return data


# ============================================================
# USER PROFILE SERIALIZERS
# ============================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serialize additional user profile information.
    """

    class Meta:
        model = UserProfile

        fields = [
            "phone_number",
            "job_title",
            "preferred_language",
            "timezone",
        ]


class UserProfileAdministrativeSerializer(serializers.ModelSerializer):
    """
    Administrative serializer for managing user profiles.
    """

    class Meta:
        model = UserProfile

        fields = [
            "phone_number",
            "job_title",
            "preferred_language",
            "timezone",
        ]


# ============================================================
# CURRENT USER SERIALIZER
# ============================================================

class CurrentUserSerializer(serializers.ModelSerializer):
    """
    Return authenticated user information, profile,
    assigned roles, and effective permissions.
    """

    profile = UserProfileSerializer(read_only=True)

    roles = serializers.SerializerMethodField()

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "date_joined",
            "profile",
            "roles",
            "permissions",
        ]

        read_only_fields = fields

    def get_roles(self, obj):
        """
        Return active roles assigned to the user.
        """

        return list(
            obj.role_assignments.filter(
                is_active=True,
                role__is_active=True,
            ).values_list(
                "role__code",
                flat=True,
            )
        )

    def get_permissions(self, obj):
        """
        Return effective permissions for the authenticated user.
        """

        from apps.accounts.services import get_user_permissions

        permissions = get_user_permissions(obj)

        if "*" in permissions:
            return ["*"]

        return sorted(permissions)


# ============================================================
# ADMINISTRATIVE USER SERIALIZERS
# ============================================================

class AdministrativeUserSerializer(serializers.ModelSerializer):
    """
    Safe user representation for administrative endpoints.
    """

    class Meta:
        model = User

        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
        ]

        read_only_fields = [
            "id",
            "date_joined",
            "last_login",
        ]


class AdministrativeUserCreateSerializer(serializers.ModelSerializer):
    """
    Create users through administrative endpoints.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=12,
        trim_whitespace=False,
    )

    class Meta:
        model = User

        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
        ]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        return User.objects.create_user(
            password=password,
            **validated_data,
        )


# ============================================================
# USER ROLE ASSIGNMENT SERIALIZER
# ============================================================

class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    """
    Administrative serializer for assigning roles to users.

    Supports:
    - Global role assignments.
    - Organization-specific assignments.
    - Facility-specific assignments.
    - Assignment validity periods.
    - Organization/facility relationship validation.
    """

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    role_code = serializers.CharField(
        source="role.code",
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    class Meta:
        model = UserRole

        fields = [
            "id",
            "user",
            "user_email",
            "role",
            "role_code",
            "organization",
            "organization_name",
            "facility",
            "facility_name",
            "assigned_by",
            "is_active",
            "valid_from",
            "valid_until",
            "assigned_at",
        ]

        read_only_fields = [
            "id",
            "assigned_by",
            "assigned_at",
        ]

    def validate(self, attrs):
        """
        Validate organization, facility, and assignment dates.
        """

        organization = attrs.get(
            "organization",
            self.instance.organization if self.instance else None,
        )

        facility = attrs.get(
            "facility",
            self.instance.facility if self.instance else None,
        )

        valid_from = attrs.get(
            "valid_from",
            self.instance.valid_from if self.instance else None,
        )

        valid_until = attrs.get(
            "valid_until",
            self.instance.valid_until if self.instance else None,
        )

        if organization and facility:
            if facility.organization_id != organization.id:
                raise serializers.ValidationError({
                    "facility": (
                        "The facility must belong directly to the "
                        "selected organization."
                    )
                })

        if valid_from and valid_until and valid_until <= valid_from:
            raise serializers.ValidationError({
                "valid_until": (
                    "The expiry must be later than the start date."
                )
            })

        return attrs


# ============================================================
# AUDIT EVENT SERIALIZER
# ============================================================

class AuditEventSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for audit event records.

    Provides related actor, organization, and facility information.
    """

    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    class Meta:
        model = AuditEvent

        fields = [
            "id",
            "actor",
            "actor_email",
            "category",
            "action",
            "target_type",
            "target_id",
            "description",
            "organization",
            "organization_name",
            "facility",
            "facility_name",
            "changes",
            "metadata",
            "ip_address",
            "created_at",
        ]

        read_only_fields = fields


# ============================================================
# PASSWORD CHANGE SERIALIZER
# ============================================================

class PasswordChangeSerializer(serializers.Serializer):
    """
    Secure password change serializer.

    Features:
    - Verify current password.
    - Require new password confirmation.
    - Enforce Django password validation.
    - Prevent reuse of current password.
    - Update password using Django's secure password hashing.
    """

    current_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    confirm_new_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    def validate_current_password(self, value):
        """
        Verify the user's existing password.
        """

        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                "Your current password is incorrect."
            )

        return value

    def validate(self, attrs):
        """
        Validate password confirmation and password strength.
        """

        user = self.context["request"].user

        # Check password confirmation.
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({
                "confirm_new_password": (
                    "The new passwords do not match."
                )
            })

        # Prevent using the existing password again.
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({
                "new_password": (
                    "Choose a password different from your current password."
                )
            })

        # Apply configured Django password validators.
        validate_password(
            attrs["new_password"],
            user=user,
        )

        return attrs

    def save(self, **kwargs):
        """
        Change the authenticated user's password.

        Uses Django's set_password() to ensure the password
        is securely hashed before database persistence.
        """

        if not hasattr(self, "validated_data"):
            raise AssertionError(
                "Call is_valid() before calling save()."
            )

        user = self.context["request"].user

        new_password = self.validated_data["new_password"]

        user.set_password(new_password)

        user.save(
            update_fields=["password"]
        )

        return user


 