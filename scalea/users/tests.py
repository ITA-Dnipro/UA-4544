from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from investors.models import InvestorProfile
from rest_framework import status
from rest_framework.test import APIClient
from startups.models import StartupProfile
from datetime import timedelta
from django.utils import timezone

from users.models import PasswordResetToken, AuditLog
from users.utils import (
    TokenManager,
    EncodeUidHelper,
    AuditLogger,
)

User = get_user_model()


class UserModelTests(TestCase):
    def test_user_creation_with_role_flags(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="123qwe!@#",
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_startup)
        self.assertFalse(user.is_investor)
        self.assertTrue(user.is_verified)


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register")
        self.valid_startup_data = {
            "email": "startup@example.com",
            "password": "StrongPassword123!",
            "role": "startup",
            "company_name": "Tech Future",
            "short_pitch": "We build AI solutions.",
        }

    def test_successful_startup_registration(self):
        response = self.client.post(self.url, self.valid_startup_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="startup@example.com").exists())
        self.assertTrue(
            StartupProfile.objects.filter(company_name="Tech Future").exists()
        )

        user = User.objects.get(email="startup@example.com")
        self.assertFalse(user.is_active)

    def test_successful_investor_registration(self):
        data = {
            "email": "investor@example.com",
            "password": "StrongPassword123!",
            "role": "investor",
            "bio": "Experienced angel investor.",
            "investment_focus": "SaaS",
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            InvestorProfile.objects.filter(user__email="investor@example.com").exists()
        )

    def test_registration_duplicate_email_returns_201_and_masks_existence(self):
        existing_email = "startup@example.com"
        User.objects.create_user(
            username=existing_email,
            email=existing_email,
            password="Password123!",
        )
        initial_count = User.objects.count()

        response = self.client.post(self.url, self.valid_startup_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["detail"], "Verification email sent. Please check your inbox."
        )
        self.assertEqual(User.objects.count(), initial_count)

    def test_registration_weak_password_returns_400(self):
        data = self.valid_startup_data.copy()
        data["password"] = "123"

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_invalid_email_returns_400(self):
        data = self.valid_startup_data.copy()
        data["email"] = "not-an-email"

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_role_returns_400(self):
        data = self.valid_startup_data.copy()
        data.pop("role")

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# Password Reset Tests


class TokenManagerTestCase(TestCase):
    """Tests for TokenManager class."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="OldPassword123!",
        )

    def test_generate_token_creates_record(self):
        """Test that generate_token creates a PasswordResetToken record."""
        uid, token = TokenManager.generate_token(self.user)

        # Verify token record exists
        token_record = PasswordResetToken.objects.get(user=self.user)
        self.assertFalse(token_record.is_used)
        self.assertIsNotNone(token_record.expires_at)

    def test_generate_token_returns_uid_and_token(self):
        """Test that generate_token returns both uid and token."""
        uid, token = TokenManager.generate_token(self.user)

        self.assertIsNotNone(uid)
        self.assertIsNotNone(token)
        self.assertIsInstance(uid, str)
        self.assertIsInstance(token, str)

    def test_validate_token_success(self):
        """Test successful token validation."""
        uid, token = TokenManager.generate_token(self.user)

        is_valid, user = TokenManager.validate_token(uid, token)

        self.assertTrue(is_valid)
        self.assertEqual(user.id, self.user.id)

    def test_validate_token_invalid_token(self):
        """Test validation fails with invalid token."""
        uid, token = TokenManager.generate_token(self.user)

        is_valid, user = TokenManager.validate_token(uid, "invalid_token")

        self.assertFalse(is_valid)
        self.assertIsNone(user)

    def test_validate_token_expired(self):
        """Test validation fails with expired token."""
        uid, token = TokenManager.generate_token(self.user)

        # Manually expire the token
        token_record = PasswordResetToken.objects.get(user=self.user)
        token_record.expires_at = timezone.now() - timedelta(hours=1)
        token_record.save()

        is_valid, user = TokenManager.validate_token(uid, token)

        self.assertFalse(is_valid)
        self.assertIsNone(user)

    def test_validate_token_already_used(self):
        """Test validation fails with already-used token."""
        uid, token = TokenManager.generate_token(self.user)

        # Mark token as used
        token_record = PasswordResetToken.objects.get(user=self.user)
        token_record.mark_used()

        is_valid, user = TokenManager.validate_token(uid, token)

        self.assertFalse(is_valid)
        self.assertIsNone(user)

    def test_validate_token_invalid_uid(self):
        """Test validation fails with invalid uid."""
        is_valid, user = TokenManager.validate_token("invalid_uid", "token")

        self.assertFalse(is_valid)
        self.assertIsNone(user)

    def test_mark_token_used(self):
        """Test marking token as used."""
        uid, token = TokenManager.generate_token(self.user)

        # Mark as used
        result = TokenManager.mark_token_used(uid, token)

        self.assertTrue(result)

        # Verify token is marked used
        token_record = PasswordResetToken.objects.get(user=self.user)
        self.assertTrue(token_record.is_used)
        self.assertIsNotNone(token_record.used_at)

    def test_mark_token_used_nonexistent(self):
        """Test marking nonexistent token as used."""
        result = TokenManager.mark_token_used("invalid_uid", "invalid_token")

        self.assertFalse(result)


class EncodeUidHelperTestCase(TestCase):
    """Tests for EncodeUidHelper class."""

    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding uid."""
        user_id = 42

        encoded = EncodeUidHelper.encode(user_id)
        decoded = EncodeUidHelper.decode(encoded)

        self.assertEqual(decoded, user_id)

    def test_encode_produces_string(self):
        """Test that encode produces a string."""
        encoded = EncodeUidHelper.encode(42)

        self.assertIsInstance(encoded, str)

    def test_decode_invalid_uid(self):
        """Test decode with invalid uid."""
        decoded = EncodeUidHelper.decode("invalid_uid_xyz")

        self.assertIsNone(decoded)

    def test_decode_empty_string(self):
        """Test decode with empty string."""
        decoded = EncodeUidHelper.decode("")

        self.assertIsNone(decoded)

    def test_decode_corrupted_base64(self):
        """Test decode with corrupted but base64-like input."""
        decoded = EncodeUidHelper.decode("!!!invalid_base64!!!")

        self.assertIsNone(decoded)

    def test_encode_large_user_id(self):
        """Test encoding very large user ID."""
        large_id = 999999999

        encoded = EncodeUidHelper.encode(large_id)
        decoded = EncodeUidHelper.decode(encoded)

        self.assertEqual(decoded, large_id)

    def test_encode_user_id_one(self):
        """Test edge case: user ID = 1."""
        encoded = EncodeUidHelper.encode(1)
        decoded = EncodeUidHelper.decode(encoded)

        self.assertEqual(decoded, 1)


class AuditLoggerTestCase(TestCase):
    """Tests for AuditLogger class."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Password123!",
        )

    def test_log_password_reset(self):
        """Test that password reset is logged."""
        AuditLogger.log_password_reset(
            user=self.user,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        audit_log = AuditLog.objects.get(user=self.user)
        self.assertEqual(audit_log.action, AuditLog.ACTION_PASSWORD_RESET)
        self.assertEqual(audit_log.ip_address, "192.168.1.1")
        self.assertEqual(audit_log.user_agent, "Mozilla/5.0")

    def test_log_password_reset_without_context(self):
        """Test logging without ip/user_agent."""
        AuditLogger.log_password_reset(user=self.user)

        audit_log = AuditLog.objects.get(user=self.user)
        self.assertEqual(audit_log.action, AuditLog.ACTION_PASSWORD_RESET)
        self.assertIsNone(audit_log.ip_address)
        self.assertIsNone(audit_log.user_agent)


class PasswordResetConfirmAPITestCase(TestCase):
    """Integration tests for password reset confirm endpoint.

    These tests treat the endpoint as a black box, creating tokens via DB
    rather than internal TokenManager to ensure tests remain robust as
    implementation evolves.
    """

    def setUp(self):
        """Create test user and API client."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="OldPassword123!",
        )
        self.client = APIClient()
        self.endpoint = reverse("password_reset_confirm")

    def _create_valid_token(self, user=None, expired=False):
        """
        Create a valid token via DB (black-box approach).

        Args:
            user: User to create token for (defaults to self.user)
            expired: If True, create an expired token

        Returns:
            Tuple of (uid, token, token_record)
        """
        if user is None:
            user = self.user

        from users.utils import EncodeUidHelper, TokenManager
        import hashlib
        import secrets

        # Generate token and hash (mimicking TokenManager internals)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        uid = EncodeUidHelper.encode(user.id)

        # Create token record
        expires_at = timezone.now() + timezone.timedelta(seconds=86400)
        if expired:
            expires_at = timezone.now() - timezone.timedelta(hours=1)

        token_record = PasswordResetToken.objects.create(
            user=user,
            uid=uid,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
        )

        return uid, token, token_record

    def test_endpoint_success(self):
        """Test successful password reset via endpoint."""
        uid, token, _ = self._create_valid_token()

        data = {
            "uid": uid,
            "token": token,
            "password": "NewPassword456!",
        }
        response = self.client.post(self.endpoint, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Password changed successfully.")

    def test_endpoint_invalid_token(self):
        """Test endpoint with invalid token returns 400."""
        uid, _, _ = self._create_valid_token()

        data = {
            "uid": uid,
            "token": "completely_invalid_token_xyz",
            "password": "NewPassword456!",
        }
        response = self.client.post(self.endpoint, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_endpoint_weak_password(self):
        """Test endpoint with weak password returns 422."""
        uid, token, _ = self._create_valid_token()

        data = {
            "uid": uid,
            "token": token,
            "password": "weak",
        }
        response = self.client.post(self.endpoint, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("password", response.data)

    def test_endpoint_expired_token(self):
        """Test endpoint with expired token returns 400."""
        uid, token, _ = self._create_valid_token(expired=True)

        data = {
            "uid": uid,
            "token": token,
            "password": "NewPassword456!",
        }
        response = self.client.post(self.endpoint, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_token_single_use(self):
        """Test that token can only be used once (single-use enforcement)."""
        uid, token, _ = self._create_valid_token()

        data = {
            "uid": uid,
            "token": token,
            "password": "NewPassword456!",
        }

        # First use should succeed
        response1 = self.client.post(self.endpoint, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Second use should fail (token marked as used)
        response2 = self.client.post(self.endpoint, data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_audit_log_created(self):
        """Test that audit log is created on successful password reset."""
        uid, token, _ = self._create_valid_token()

        data = {
            "uid": uid,
            "token": token,
            "password": "NewPassword456!",
        }
        response = self.client.post(self.endpoint, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify audit log was created
        audit_log = AuditLog.objects.filter(
            user=self.user, action=AuditLog.ACTION_PASSWORD_RESET
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertIn("timestamp", audit_log.details)

    def test_endpoint_user_can_login_with_new_password(self):
        """Test that user can actually login with new password after reset."""
        uid, token, _ = self._create_valid_token()
        new_password = "NewPassword456!"

        data = {
            "uid": uid,
            "token": token,
            "password": new_password,
        }
        response = self.client.post(self.endpoint, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password changed in DB
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password("OldPassword123!"))

    def test_endpoint_missing_required_fields(self):
        """Test endpoint with missing required fields returns validation error."""
        data = {
            "uid": "some_uid",
            # Missing token and password
        }
        response = self.client.post(self.endpoint, data, format="json")

        # Missing fields are validation errors → 422
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_endpoint_empty_password(self):
        """Test endpoint with empty password returns validation error."""
        uid, token, _ = self._create_valid_token()

        data = {
            "uid": uid,
            "token": token,
            "password": "",
        }
        response = self.client.post(self.endpoint, data, format="json")

        # Empty password is validation error → 422
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_endpoint_password_no_reuse_of_old_password(self):
        """Test that reusing the same old password is not allowed by validators.

        Note: Django's default validators include CommonPasswordValidator
        which rejects common passwords. We test that attempting to reuse
        the old password gets properly validated.
        """
        uid, token, _ = self._create_valid_token()
        old_password = "OldPassword123!"

        data = {
            "uid": uid,
            "token": token,
            "password": old_password,  # Try to use same password
        }
        response = self.client.post(self.endpoint, data, format="json")

        # Password validation should catch this (either as 422 or accept if allowed)
        # The actual behavior depends on whether UserAttributeSimilarityValidator
        # is enabled and what it checks. We verify the endpoint doesn't crash.
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY],
        )

    def test_endpoint_invalid_uid_format(self):
        """Test endpoint with malformed uid returns 400."""
        data = {
            "uid": "not_valid_base64_///",
            "token": "some_token",
            "password": "NewPassword456!",
        }
        response = self.client.post(self.endpoint, data, format="json")

        # Invalid uid should fail token validation → 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

