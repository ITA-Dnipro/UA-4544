from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.core import exceptions
from django.db import transaction
from investors.models import InvestorProfile
from startups.models import StartupProfile

from .utils import TokenManager

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=["startup", "investor"])
    company_name = serializers.CharField(required=False, allow_blank=True, default="")
    short_pitch = serializers.CharField(required=False, allow_blank=True, default="")
    website = serializers.URLField(required=False, allow_blank=True, default="")
    bio = serializers.CharField(required=False, allow_blank=True, default="")
    investment_focus = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_email(self, value):
        normalized_email = User.objects.normalize_email(value)
        return normalized_email.lower()

    def validate_password(self, value):
        try:
            validate_password(value)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from e
        return value

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("role")
        password = validated_data.pop("password")
        email = validated_data.pop("email")

        user = User.objects.filter(email=email).first()

        if user:
            self.send_already_registered_email(user)
            return user

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False,
            is_startup=(role == "startup"),
            is_investor=(role == "investor"),
        )

        if role == "startup":
            StartupProfile.objects.create(
                user=user,
                company_name=validated_data.get("company_name", ""),
                description=validated_data.get("short_pitch", ""),
                website=validated_data.get("website", ""),
            )
        else:
            InvestorProfile.objects.create(
                user=user,
                company_name=validated_data.get("company_name", ""),
                bio=validated_data.get("bio", ""),
                investment_focus=validated_data.get("investment_focus", ""),
            )

        self.send_verification_email(user)
        return user

    def send_verification_email(self, user):
        # TODO(i-taras): Implement actual SMTP dispatch & activation token logic [#99]
        # Users will be LOCKED OUT until this method is implemented
        # and the activation endpoint is ready.
        # This is a placeholder to allow the registration schema to merge.
        pass

    def send_already_registered_email(self, user):
        # TODO(i-taras): Implement resend logic for verification emails [#99]
        # This is a placeholder to allow the registration schema to merge and
        # NO email is actually dispatched.
        pass


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset with token and new password.

    Validates token, uid, and password complexity.
    """

    uid = serializers.CharField(required=True, write_only=True)
    token = serializers.CharField(required=True, write_only=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)

    def validate_password(self, value):
        """Validate password meets complexity requirements."""
        try:
            validate_password(value)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from e
        return value

    def validate(self, attrs):
        """
        Validate that uid and token combination is valid and not expired/used.

        Note: For single-use enforcement, the actual token consumption happens
        atomically in save() using TokenManager.consume_token() to prevent
        race conditions.

        Raises:
            ValidationError: If token is invalid, expired, or already used
        """
        uid = attrs.get("uid")
        token = attrs.get("token")

        # Pre-validate token format without consuming it yet
        # (actual consumption happens atomically in save())
        is_valid, user = TokenManager.validate_token(uid, token)

        if not is_valid or user is None:
            raise serializers.ValidationError({"detail": "Invalid or expired token."})

        # Store uid and token for atomic consumption in save()
        attrs["_user"] = user
        attrs["_uid"] = uid
        attrs["_token"] = token
        return attrs

    def save(self):
        """
        Atomically consume token, update password, and revoke sessions.

        Returns:
            The updated User instance
        """
        new_password = self._validated_data.get("password")
        uid = self._validated_data.get("_uid")
        token = self._validated_data.get("_token")

        # Atomically consume the token (prevents race conditions)
        is_valid, user = TokenManager.consume_token(uid, token)

        if not is_valid or user is None:
            raise serializers.ValidationError(
                {"detail": "Invalid or expired token."}
            )

        # Update password
        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Revoke sessions and tokens
        from .utils import SessionRevoker

        SessionRevoker.revoke_all_sessions(user)
        SessionRevoker.revoke_refresh_tokens(user)

        return user
