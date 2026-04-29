"""
Utilities for password reset functionality.

Provides token generation, validation, encoding/decoding, and session management.
"""

import base64
import hashlib
import secrets
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import AuditLog, PasswordResetToken

User = get_user_model()


class TokenManager:
    """Manages password reset tokens: generation, validation, marking as used."""

    TOKEN_LENGTH = getattr(settings, "PASSWORD_RESET_TOKEN_LENGTH", 32)
    TOKEN_TIMEOUT = getattr(settings, "PASSWORD_RESET_TIMEOUT", 86400)  # 24 hours

    @staticmethod
    def generate_token(user: User) -> Tuple[str, str]:
        """
        Generate a password reset token for the user.

        Args:
            user: The User instance to generate token for

        Returns:
            Tuple of (uid, token) where token is the plain token (send to user)
        """
        # Generate random token
        token = secrets.token_urlsafe(TokenManager.TOKEN_LENGTH)

        # Hash the token for storage
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Encode uid
        uid = EncodeUidHelper.encode(user.id)

        # Calculate expiry
        expires_at = timezone.now() + timezone.timedelta(
            seconds=TokenManager.TOKEN_TIMEOUT
        )

        # Create token record in DB
        PasswordResetToken.objects.create(
            user=user,
            uid=uid,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        return uid, token

    @staticmethod
    def validate_token(uid: str, token: str) -> Tuple[bool, Optional[User]]:
        """
        Validate a password reset token.

        Args:
            uid: The encoded user ID
            token: The plain token

        Returns:
            Tuple of (is_valid, user) where user is None if invalid
        """
        try:
            # Decode uid to get user ID
            user_id = EncodeUidHelper.decode(uid)
            if user_id is None:
                return False, None

            # Hash the token
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Query token record
            token_record = PasswordResetToken.objects.select_related("user").get(
                uid=uid,
                token_hash=token_hash,
            )

            # Check if already used
            if token_record.is_used:
                return False, None

            # Check if expired
            if token_record.is_expired():
                return False, None

            return True, token_record.user

        except (
            ValueError,
            PasswordResetToken.DoesNotExist,
        ):
            return False, None

    @staticmethod
    def mark_token_used(uid: str, token: str) -> bool:
        """
        Mark a token as used (single-use enforcement).

        Args:
            uid: The encoded user ID
            token: The plain token

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            token_record = PasswordResetToken.objects.get(
                uid=uid,
                token_hash=token_hash,
            )
            token_record.mark_used()
            return True
        except PasswordResetToken.DoesNotExist:
            return False


class EncodeUidHelper:
    """Helper for encoding/decoding user IDs."""

    @staticmethod
    def encode(user_id: int) -> str:
        """
        Encode a user ID to a URL-safe string.

        Args:
            user_id: The user ID integer

        Returns:
            Base64-encoded user ID
        """
        return base64.urlsafe_b64encode(str(user_id).encode()).decode().rstrip("=")

    @staticmethod
    def decode(encoded_uid: str) -> Optional[int]:
        """
        Decode an encoded user ID.

        Args:
            encoded_uid: The base64-encoded user ID

        Returns:
            The user ID integer, or None if invalid
        """
        try:
            # Add padding back
            padding = 4 - (len(encoded_uid) % 4)
            if padding != 4:
                encoded_uid += "=" * padding

            decoded = base64.urlsafe_b64decode(encoded_uid).decode()
            return int(decoded)
        except (ValueError, TypeError):
            return None


class SessionRevoker:
    """Manages session and token revocation on password change."""

    @staticmethod
    def revoke_all_sessions(user: User) -> None:
        """
        Revoke all active sessions for a user.

        This logs the user out from all devices.

        Args:
            user: The User instance
        """
        from django.contrib.sessions.models import Session

        # Delete all sessions for this user
        for session in Session.objects.all():
            try:
                session_data = session.get_decoded()
                if session_data.get("_auth_user_id") == str(user.id):
                    session.delete()
            except Exception:
                # Session data might be corrupted; skip
                pass

    @staticmethod
    def revoke_refresh_tokens(user: User) -> None:
        """
        Revoke all refresh tokens for a user (if using token-based auth).

        Note: Implement this if you're using JWT or similar token-based auth.
        Currently a placeholder for future implementation.

        Args:
            user: The User instance
        """
        # TODO: Implement refresh token blacklisting when JWT auth is added
        pass


class AuditLogger:
    """Logs password reset operations for compliance and auditing."""

    @staticmethod
    def log_password_reset(
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Log a password reset action.

        Args:
            user: The User instance
            ip_address: Client IP address
            user_agent: Client user agent
        """
        AuditLog.objects.create(
            user=user,
            action=AuditLog.ACTION_PASSWORD_RESET,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "timestamp": timezone.now().isoformat(),
            },
        )


class RequestContextHelper:
    """Helper to extract request context (IP, user agent)."""

    @staticmethod
    def get_client_ip(request) -> Optional[str]:
        """
        Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: Django request object

        Returns:
            Client IP address or None
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    @staticmethod
    def get_user_agent(request) -> Optional[str]:
        """
        Extract user agent from request.

        Args:
            request: Django request object

        Returns:
            User agent string or None
        """
        return request.META.get("HTTP_USER_AGENT")
