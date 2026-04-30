import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from users.tokens import password_reset_token

from .serializers import RegisterSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()

        if user:
            token = password_reset_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            combined_token = f'{uid}.{token}'
            reset_url = f'{settings.FRONTEND_URL}/reset-password/{combined_token}/'

            html_message = render_to_string(
                'email/password_reset.html',
                {
                    'reset_url': reset_url,
                },
            )
            email_msg = EmailMultiAlternatives(
                subject='Password Reset — Scalea',
                body=f'Reset your password: {reset_url}',
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )
            email_msg.attach_alternative(html_message, 'text/html')
            try:
                email_msg.send(fail_silently=False)
            except Exception:
                logger.exception('Failed to send password reset email')

        return Response(
            {'detail': 'If this email exists, you will receive a reset link.'},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            uid, token = raw_token.split('.', 1)
            decoded_uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.filter(id=decoded_uid).first()
        except (ValueError, TypeError):
            user = None

        if not user or not password_reset_token.check_token(user, token):
            return Response(
                {'detail': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        user.save()
        logger.info('Password reset for user: %s', user.pk)

        return Response(
            {'detail': 'Password changed successfully'},
            status=status.HTTP_200_OK,
        )


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *_args, **_kwargs):
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