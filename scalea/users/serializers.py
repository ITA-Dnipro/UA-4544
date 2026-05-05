from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from investors.models import InvestorProfile
from startups.models import StartupProfile

User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=['startup', 'investor'])
    company_name = serializers.CharField(required=False, allow_blank=True, default='')
    short_pitch = serializers.CharField(required=False, allow_blank=True, default='')
    website = serializers.URLField(required=False, allow_blank=True, default='')
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    investment_focus = serializers.CharField(
        required=False, allow_blank=True, default=''
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
        role = validated_data.pop('role')
        password = validated_data.pop('password')
        email = validated_data.pop('email')

        user = User.objects.filter(email=email).first()

        if user:
            self.send_already_registered_email(user)
            return user

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False,
            is_startup=(role == 'startup'),
            is_investor=(role == 'investor'),
        )

        if role == 'startup':
            StartupProfile.objects.create(
                user=user,
                company_name=validated_data.get('company_name', ''),
                description=validated_data.get('short_pitch', ''),
                website=validated_data.get('website', ''),
            )
        else:
            InvestorProfile.objects.create(
                user=user,
                company_name=validated_data.get('company_name', ''),
                bio=validated_data.get('bio', ''),
                investment_focus=validated_data.get('investment_focus', ''),
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


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    remember = serializers.BooleanField(required=False, default=False)
    role = serializers.ChoiceField(choices=['startup', 'investor'], required=True)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        password = attrs['password']
        requested_role = attrs['role']

        user = User.objects.filter(email=email).first()

        if not user or not user.check_password(password) or not user.is_active:
            raise serializers.ValidationError(
                {'detail': 'Invalid email or password.'},
                code='authorization',
            )

        if requested_role == 'startup' and not user.is_startup:
            raise serializers.ValidationError(
                {'detail': 'Invalid email or password.'},
                code='authorization',
            )

        if requested_role == 'investor' and not user.is_investor:
            raise serializers.ValidationError(
                {'detail': 'Invalid email or password.'},
                code='authorization',
            )

        attrs['user'] = user
        attrs['email'] = email
        attrs['role'] = requested_role
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate(self, attrs):
        try:
            attrs['token_obj'] = RefreshToken(attrs['refresh'])
        except TokenError as exc:
            raise serializers.ValidationError(
                {'detail': 'Invalid or expired token.'}
            ) from exc
        return attrs

    def save(self):
        self.validated_data['token_obj'].blacklist()
