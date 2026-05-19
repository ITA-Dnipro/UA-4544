from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.db import transaction
from investors.models import InvestorProfile
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
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
    role = serializers.ChoiceField(choices=['startup', 'investor', 'org_admin'])
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
            if not user.check_password(password):
                self.send_already_registered_email(user)
                return user

            if (
                (role == 'startup' and user.is_startup)
                or (role == 'investor' and user.is_investor)
                or (role == 'org_admin' and user.is_org_admin)
            ):
                raise serializers.ValidationError(
                    {'role': f'You already have a {role} profile.'}
                )

            if role == 'startup':
                user.is_startup = True
            elif role == 'investor':
                user.is_investor = True
            elif role == 'org_admin':
                user.is_org_admin = True
                user.is_verified = False

            user.save()
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_active=False,
                is_startup=(role == 'startup'),
                is_investor=(role == 'investor'),
                is_org_admin=(role == 'org_admin'),
            )

        self._create_role_profile(user, role, validated_data)

        self.send_verification_email(user)
        return user

    def _create_role_profile(self, user, role, data):
        if role == 'startup':
            StartupProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': data.get('company_name', ''),
                    'description': data.get('short_pitch', ''),
                    'website': data.get('website', ''),
                },
            )
        elif role == 'investor':
            InvestorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': data.get('company_name', ''),
                    'bio': data.get('bio', ''),
                    'investment_focus': data.get('investment_focus', ''),
                },
            )

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
    role = serializers.ChoiceField(
        choices=['startup', 'investor', 'org_admin'], required=True
    )

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        password = attrs['password']
        requested_role = attrs['role']
        user = User.objects.filter(email=email).first()

        if not user or not user.is_active:
            raise serializers.ValidationError(
                {'detail': 'Invalid email or password.'},
                code='authorization',
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {'detail': 'Invalid email or password.'},
                code='authorization',
            )

        role_check = {
            'startup': user.is_startup,
            'investor': user.is_investor,
            'org_admin': user.is_org_admin,
        }

        if not role_check.get(requested_role):
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


class AdminUserModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'is_org_admin', 'is_verified', 'created_at')
