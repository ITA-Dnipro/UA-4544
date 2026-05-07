import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import PasswordResetAudit
from .security import (
    clear_failures,
    is_locked,
    is_password_reset_locked,
    register_failure,
    register_password_reset_request,
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

        if is_password_reset_locked(email):
            return Response(
                {
                    'detail': 'Too many password reset requests for this email. Try again later.'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        register_password_reset_request(email)
        user = User.objects.filter(email=email).first()

        PasswordResetAudit.objects.create(
            user=user, email=email, ip_address=get_client_ip(request)
        )

        if user:
            token = password_reset_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            combined_token = f'{uid}.{token}'
            reset_url = (
                f'{settings.FRONTEND_URL}/reset-password/?token={combined_token}'
            )

            html_message = render_to_string(
                'email/password_reset.html',
                {'reset_url': reset_url},
            )

            email_msg = EmailMultiAlternatives(
                subject='Password Reset — Scalea',
                body=f'Reset your password: {reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
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
        except (ValueError, TypeError, Exception):
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

    def create(self, request, *args, **kwargs): # noqa: ARG002
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
                    'role': serializer.validated_data.get('role'),
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
