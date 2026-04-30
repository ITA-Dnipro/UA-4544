import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)

from users.utils import (
    TokenManager,
    SessionRevoker,
    AuditLogger,
    RequestContextHelper,
)
from .serializers import RegisterSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()

        if user:
            uid, token = TokenManager.generate_token(user)

            combined_token = f"{uid}.{token}"
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{combined_token}/"

            email_msg = EmailMultiAlternatives(
                subject="Password Reset — Scalea",
                body=f"Reset your password: {reset_url}",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )
            email_msg.send(fail_silently=True)

        return Response(
            {"detail": "If this email exists, you will receive a reset link."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]
        uid_from_data = serializer.validated_data.get("uid", "")

        # Support both combined token format (uid.token) and separate uid + token format
        if "." in raw_token and not uid_from_data:
            # Combined format: "uid.token"
            try:
                uid, token = raw_token.split(".", 1)
            except ValueError:
                return Response(
                    {"detail": "Invalid or expired token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Separate format: uid and token in different fields
            uid = uid_from_data or ""
            token = raw_token

        if not uid or not token:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate token atomically (single-use enforcement)
        is_valid, user = TokenManager.consume_token(uid, token)

        if not is_valid or not user:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(password)
        user.save()

        # Revoke active sessions and refresh tokens
        SessionRevoker.revoke_all_sessions(user)
        SessionRevoker.revoke_refresh_tokens(user)

        # Log the password reset action
        ip_address = RequestContextHelper.get_client_ip(request)
        user_agent = RequestContextHelper.get_user_agent(request)
        AuditLogger.log_password_reset(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Password reset for user %s", user.pk)

        return Response(
            {"detail": "Password changed successfully"},
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
                "email": user.email,
                "detail": "Verification email sent. Please check your inbox.",
            },
            status=status.HTTP_201_CREATED,
        )