from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import RegisterSerializer, PasswordResetConfirmSerializer
from .utils import AuditLogger, RequestContextHelper

User = get_user_model()


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


class PasswordResetConfirmView(generics.CreateAPIView):
    """
    API endpoint for confirming password reset.

    POST /api/auth/password-reset/confirm/
    {
        "uid": "encoded_user_id",
        "token": "token_string",
        "password": "NewP@ssw0rd!"
    }

    Returns:
        - 200 OK: Password reset successful
        - 400 Bad Request: Invalid or expired token
        - 422 Unprocessable Entity: Password validation failed
    """

    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """Handle POST request for password reset confirmation."""
        serializer = self.get_serializer(data=request.data)

        # Check if serializer is valid
        if not serializer.is_valid():
            # Distinguish between token validation errors (400) and
            # other field validation errors (422)
            if "detail" in serializer.errors:
                # Token validation failed → 400 Bad Request
                return Response(
                    {"detail": serializer.errors["detail"][0]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Other validation errors (password, missing fields, etc) → 422
                return Response(
                    serializer.errors,
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

        # Save and update password
        user = serializer.save()

        # Extract request context for audit log
        ip_address = RequestContextHelper.get_client_ip(request)
        user_agent = RequestContextHelper.get_user_agent(request)

        # Create audit log entry
        AuditLogger.log_password_reset(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )
