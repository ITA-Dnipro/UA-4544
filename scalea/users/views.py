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

from users.models import PasswordResetAuditLog, PasswordResetToken
from users.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from users.tokens import hash_token, password_reset_token

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
            token = password_reset_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Store token hash for single-use tracking
            token_hash = hash_token(token)
            PasswordResetToken.objects.create(
                user=user,
                token_hash=token_hash,
            )

            combined_token = f"{uid}.{token}"
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{combined_token}/"

            html_message = render_to_string(
                "email/password_reset.html",
                {
                    "reset_url": reset_url,
                },
            )
            email_msg = EmailMultiAlternatives(
                subject="Password Reset — Scalea",
                body=f"Reset your password: {reset_url}",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )
            email_msg.attach_alternative(html_message, "text/html")
            try:
                email_msg.send(fail_silently=False)
                # Log successful password reset request
                client_ip = self._get_client_ip(request)
                user_agent = self._get_user_agent(request)
                PasswordResetAuditLog.objects.create(
                    user=user,
                    action="request",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    details={"success": True},
                )
            except Exception:
                logger.exception("Failed to send password reset email")

        return Response(
            {"detail": "If this email exists, you will receive a reset link."},
            status=status.HTTP_200_OK,
        )

    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _get_user_agent(self, request):
        """Extract user agent from request."""
        return request.META.get("HTTP_USER_AGENT", "")


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def get_user_agent(self, request):
        """Extract user agent from request."""
        return request.META.get("HTTP_USER_AGENT", "")

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            # Return 422 for password validation errors, 400 for other errors
            if "password" in serializer.errors:
                return Response(
                    serializer.errors,
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]
        uid = serializer.validated_data.get("uid", "")

        client_ip = self.get_client_ip(request)
        user_agent = self.get_user_agent(request)

        # Parse token: either combined format or separate uid/token
        try:
            if "." in raw_token:
                # Combined format: uid.token
                uid, token = raw_token.split(".", 1)
            else:
                # Separate uid and token
                token = raw_token
                if not uid:
                    return Response(
                        {"detail": "Invalid or expired token."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            decoded_uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.filter(id=decoded_uid).first()
        except (ValueError, TypeError):
            user = None

        # Validate user and token
        if not user or not password_reset_token.check_token(user, token):
            # Log failed reset attempt
            if user:
                PasswordResetAuditLog.objects.create(
                    user=user,
                    action="failed",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    details={"reason": "invalid_or_expired_token"},
                )
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if token has already been used
        token_hash = hash_token(token)
        reset_token_record = PasswordResetToken.objects.filter(
            user=user,
            token_hash=token_hash,
        ).first()

        if reset_token_record and reset_token_record.is_used:
            PasswordResetAuditLog.objects.create(
                user=user,
                action="failed",
                ip_address=client_ip,
                user_agent=user_agent,
                details={"reason": "token_already_used"},
            )
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(password)
        user.save()

        # Mark token as used
        if reset_token_record:
            reset_token_record.mark_as_used()

        # Revoke all refresh tokens (logout from all devices)
        # Note: Token revocation depends on your authentication strategy
        # If using JWT tokens, implement token blacklisting accordingly
        try:
            # Attempt to revoke tokens if jwt tokens are used
            # This is optional and depends on your token strategy
            pass
        except Exception:
            # Token revocation is optional; log but don't fail
            logger.warning("Failed to revoke tokens for user: %s", user.pk)

        # Log successful password reset
        PasswordResetAuditLog.objects.create(
            user=user,
            action="confirm",
            ip_address=client_ip,
            user_agent=user_agent,
            details={"success": True},
        )

        logger.info(
            "Password reset confirmed for user: %s from IP: %s", user.pk, client_ip
        )

        return Response(
            {"detail": "Password changed successfully."},
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
