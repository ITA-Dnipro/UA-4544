import hashlib
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from investors.models import InvestorProfile
from investors.serializers import (
    InvestorProfileUpdateSerializer,
    InvestorPublicProfileSerializer,
)
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from startups.models import StartupProfile
from startups.permissions import IsProfileOwnerOrAdmin
from startups.serializers import (
    StartupProfileUpdateSerializer,
    StartupPublicProfileSerializer,
)

from .models import PasswordResetAudit
from .security import (
    clear_failures,
    is_locked,
    register_failure,
)
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from .tokens import password_reset_token

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def mask_email_for_log(email):
    return hashlib.sha256(email.encode()).hexdigest()[:10] + '...'


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()

        PasswordResetAudit.objects.create(
            user=user, email=email, ip_address=get_client_ip(request)
        )

        if user:
            token = password_reset_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            combined_token = f'{uid}.{token}'
            reset_url = f'{settings.FRONTEND_URL}/reset-password/{combined_token}/'

            display_name = (
                user.first_name
                or user.get_full_name().strip()
                or user.username
                or user.email.split('@')[0]
            )
            expiry_minutes = max(1, settings.PASSWORD_RESET_TIMEOUT // 60)
            email_context = {
                'user_name': display_name,
                'reset_url': reset_url,
                'expiry_minutes': expiry_minutes,
            }

            text_message = render_to_string('email/password_reset.txt', email_context)

            html_message = render_to_string(
                'email/password_reset.html',
                email_context,
            )

            reply_to = (
                settings.EMAIL_REPLY_TO.strip() if settings.EMAIL_REPLY_TO else ''
            )
            email_kwargs = {
                'subject': 'Password Reset — Scalea',
                'body': text_message,
                'from_email': settings.DEFAULT_FROM_EMAIL,
                'to': [user.email],
            }
            if reply_to:
                email_kwargs['reply_to'] = [reply_to]

            email_msg = EmailMultiAlternatives(**email_kwargs)
            email_msg.attach_alternative(html_message, 'text/html')

            try:
                email_msg.send(fail_silently=False)
            except Exception:
                logger.exception(
                    'Failed to send password reset email to %s',
                    mask_email_for_log(email),
                )

        return Response(
            {'detail': 'If the email exists, you will receive reset instructions.'},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            uid_b64, token = raw_token.split('.', 1)
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.filter(id=uid).first()
        except (ValueError, TypeError):
            user = None

        if not user or not password_reset_token.check_token(user, token):
            return Response(
                {'detail': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(password)
            user.save()

            for outstanding in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=outstanding)

        logger.info('Password reset successful for user ID: %s', user.pk)

        return Response(
            {'detail': 'Password changed successfully'},
            status=status.HTTP_200_OK,
        )


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    def create(self, request, *args, **kwargs):  # noqa: ARG002
        if settings.RECAPTCHA_SECRET_KEY:
            token = request.data.get('recaptcha_token')
            try:
                resp = requests.post(
                    'https://www.google.com/recaptcha/api/siteverify',
                    data={
                        'secret': settings.RECAPTCHA_SECRET_KEY,
                        'response': token,
                    },
                    timeout=5,
                )
                if not resp.json().get('success'):
                    return Response(
                        {'detail': 'Invalid captcha. Please try again.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except requests.RequestException:
                logger.warning('reCAPTCHA verification request failed')
                return Response(
                    {
                        'detail': 'Captcha service temporarily unavailable. Please try again.'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                'email': user.email,
                'detail': 'Verification email sent. Please check your inbox.',
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        raw_email = request.data.get('email')
        email = raw_email.strip().lower() if isinstance(raw_email, str) else ''

        if email and is_locked(email):
            return Response(
                {'detail': ['Too many failed attempts. Try again later.']},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            if 'detail' in serializer.errors:
                if email:
                    register_failure(email)
                return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        remember = serializer.validated_data['remember']
        role = serializer.validated_data.get('role')

        if role == 'org_admin' and not user.is_verified:
            return Response(
                {'detail': 'Your administrative account is pending approval.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        clear_failures(email)

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        if remember:
            refresh.set_exp(lifetime=timedelta(days=30))
            access.set_exp(lifetime=timedelta(hours=12))

        return Response(
            {
                'access': str(access),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': role,
                },
            },
            status=status.HTTP_200_OK,
        )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'refresh'


class LogoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'logout'

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UniversalProfileDetailView(generics.RetrieveUpdateAPIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsProfileOwnerOrAdmin()]

    def get_object(self):
        pk = self.kwargs.get('pk')
        user = get_object_or_404(User, pk=pk)

        if user.is_startup:
            queryset = StartupProfile.objects.annotate(
                followers_count=Count('savedstartup', distinct=True),
                projects_count=Count('projects', distinct=True),
            )
            obj = get_object_or_404(queryset, user=user)

            if not obj.is_published:
                user_auth = self.request.user
                is_owner = user_auth.is_authenticated and user_auth == obj.user
                is_admin = user_auth.is_authenticated and (
                    user_auth.is_staff or user_auth.is_superuser
                )

                if not (is_owner or is_admin):
                    raise Http404('No StartupProfile matches the given query.')
        else:
            obj = get_object_or_404(InvestorProfile, user=user)

        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        obj = self.get_object()
        is_update = self.request.method in ['PUT', 'PATCH']

        serializer_map = {
            StartupProfile: {
                'read': StartupPublicProfileSerializer,
                'update': StartupProfileUpdateSerializer,
            },
            InvestorProfile: {
                'read': InvestorPublicProfileSerializer,
                'update': InvestorProfileUpdateSerializer,
            },
        }

        serializers = serializer_map.get(obj.__class__)
        if not serializers:
            raise ValueError(f'No serializers found for {obj.__class__}')

        return serializers['update'] if is_update else serializers['read']

    def update(self, request, *args, **kwargs):  # noqa: ARG002
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        instance = self.get_object()
        if isinstance(instance, StartupProfile):
            response_serializer = StartupPublicProfileSerializer(instance)
        else:
            response_serializer = InvestorPublicProfileSerializer(instance)

        return Response(response_serializer.data)
