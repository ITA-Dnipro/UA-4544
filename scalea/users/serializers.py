from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.db import transaction
from investors.models import InvestorProfile
from rest_framework import serializers
from startups.models import StartupProfile

User = get_user_model()


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
        pass

    def send_already_registered_email(self, user):
        pass
