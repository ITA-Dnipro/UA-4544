from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from startups.models import StartupProfile
from investors.models import InvestorProfile

User = get_user_model()

class DuplicateEmailError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'A user with this email already exists.'
    default_code = 'duplicate_email'

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=['startup', 'investor'])
    company_name = serializers.CharField(required=False, allow_blank=True, default='')
    short_pitch = serializers.CharField(required=False, allow_blank=True, default='')
    website = serializers.URLField(required=False, allow_blank=True, default='')
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    investment_focus = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise DuplicateEmailError()
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop('role')
        password = validated_data.pop('password')
        email = validated_data.pop('email')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False,
            is_startup=(role == 'startup'),
            is_investor=(role == 'investor')
        )

        if role == 'startup':
            StartupProfile.objects.create(
                user=user,
                company_name=validated_data.get('company_name', ''),
                description=validated_data.get('short_pitch', ''),
                website=validated_data.get('website', '')
            )
        else:
            InvestorProfile.objects.create(
                user=user,
                company_name=validated_data.get('company_name', ''),
                bio=validated_data.get('bio', ''),
                investment_focus=validated_data.get('investment_focus', '')
            )

        self.send_verification_email(user)
        return user

    def send_verification_email(self, user):
        pass