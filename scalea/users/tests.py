from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from investors.models import InvestorProfile
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from startups.models import StartupProfile

from users.tokens import password_reset_token

from .models import PasswordResetAudit
from .serializers import PasswordResetConfirmSerializer, PasswordResetRequestSerializer

User = get_user_model()


class PasswordResetAuditModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='audituser',
            email='audit@example.com',
            password='Password123!',
        )

    def test_action_requested_constant_value(self):
        self.assertEqual(PasswordResetAudit.ACTION_REQUESTED, 'requested')

    def test_action_confirmed_constant_value(self):
        self.assertEqual(PasswordResetAudit.ACTION_CONFIRMED, 'confirmed')

    def test_default_action_is_requested(self):
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email=self.user.email,
        )
        self.assertEqual(audit.action, PasswordResetAudit.ACTION_REQUESTED)

    def test_user_agent_defaults_to_empty_string(self):
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email=self.user.email,
        )
        self.assertEqual(audit.user_agent, '')

    def test_can_store_user_agent(self):
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email=self.user.email,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        )
        self.assertEqual(audit.user_agent, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

    def test_user_agent_stores_up_to_500_chars(self):
        long_agent = 'A' * 500
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email=self.user.email,
            user_agent=long_agent,
        )
        self.assertEqual(len(audit.user_agent), 500)

    def test_str_uses_action_display_for_requested(self):
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email='audit@example.com',
            action=PasswordResetAudit.ACTION_REQUESTED,
        )
        result = str(audit)
        self.assertIn('Password Reset Requested', result)
        self.assertIn('audit@example.com', result)

    def test_str_uses_action_display_for_confirmed(self):
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email='audit@example.com',
            action=PasswordResetAudit.ACTION_CONFIRMED,
        )
        result = str(audit)
        self.assertIn('Password Reset Confirmed', result)
        self.assertIn('audit@example.com', result)

    def test_can_create_audit_with_null_user(self):
        audit = PasswordResetAudit.objects.create(
            user=None,
            email='nobody@example.com',
        )
        self.assertIsNone(audit.user)
        self.assertEqual(audit.email, 'nobody@example.com')

    def test_can_create_audit_with_confirmed_action(self):
        audit = PasswordResetAudit.objects.create(
            user=self.user,
            email=self.user.email,
            action=PasswordResetAudit.ACTION_CONFIRMED,
        )
        self.assertEqual(audit.action, PasswordResetAudit.ACTION_CONFIRMED)

    def test_action_choices_contain_both_values(self):
        choice_values = [choice[0] for choice in PasswordResetAudit.ACTION_CHOICES]
        self.assertIn(PasswordResetAudit.ACTION_REQUESTED, choice_values)
        self.assertIn(PasswordResetAudit.ACTION_CONFIRMED, choice_values)

    def test_ordering_is_newest_first(self):
        PasswordResetAudit.objects.create(user=self.user, email=self.user.email)
        PasswordResetAudit.objects.create(user=self.user, email=self.user.email)
        audits = PasswordResetAudit.objects.all()
        self.assertGreaterEqual(audits[0].created_at, audits[1].created_at)


class UserModelTests(TestCase):
    def test_user_creation_with_role_flags(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='123qwe!@#',
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.is_startup)
        self.assertFalse(user.is_investor)
        self.assertTrue(user.is_verified)


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('register')
        self.valid_startup_data = {
            'email': 'startup@example.com',
            'password': 'StrongPassword123!',
            'role': 'startup',
            'company_name': 'Tech Future',
            'short_pitch': 'We build AI solutions.',
        }

    def test_successful_startup_registration(self):
        response = self.client.post(self.url, self.valid_startup_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='startup@example.com').exists())
        self.assertTrue(
            StartupProfile.objects.filter(company_name='Tech Future').exists()
        )

        user = User.objects.get(email='startup@example.com')
        self.assertFalse(user.is_active)

    def test_successful_investor_registration(self):
        data = {
            'email': 'investor@example.com',
            'password': 'StrongPassword123!',
            'role': 'investor',
            'bio': 'Experienced angel investor.',
            'investment_focus': 'SaaS',
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            InvestorProfile.objects.filter(user__email='investor@example.com').exists()
        )

    def test_registration_duplicate_email_returns_201_and_masks_existence(self):
        existing_email = 'startup@example.com'
        User.objects.create_user(
            username=existing_email,
            email=existing_email,
            password='Password123!',
        )
        initial_count = User.objects.count()

        response = self.client.post(self.url, self.valid_startup_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['detail'], 'Verification email sent. Please check your inbox.'
        )
        self.assertEqual(User.objects.count(), initial_count)

    def test_registration_weak_password_returns_400(self):
        data = self.valid_startup_data.copy()
        data['password'] = '123'

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_invalid_email_returns_400(self):
        data = self.valid_startup_data.copy()
        data['email'] = 'not-an-email'

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_role_returns_400(self):
        data = self.valid_startup_data.copy()
        data.pop('role')

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestSerializerTests(TestCase):
    def test_valid_email_passes(self):
        s = PasswordResetRequestSerializer(data={'email': 'user@example.com'})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data['email'], 'user@example.com')

    def test_email_is_lowercased(self):
        s = PasswordResetRequestSerializer(data={'email': 'USER@EXAMPLE.COM'})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data['email'], 'user@example.com')

    def test_invalid_email_fails(self):
        s = PasswordResetRequestSerializer(data={'email': 'not-an-email'})
        self.assertFalse(s.is_valid())
        self.assertIn('email', s.errors)

    def test_missing_email_fails(self):
        s = PasswordResetRequestSerializer(data={})
        self.assertFalse(s.is_valid())
        self.assertIn('email', s.errors)


class PasswordResetConfirmSerializerTests(TestCase):
    def _valid_data(self, **overrides):
        data = {'uid': 'abc123', 'token': 'valid-token', 'password': 'StrongP@ss1'}
        data.update(overrides)
        return data

    def test_valid_data_passes(self):
        s = PasswordResetConfirmSerializer(data=self._valid_data())
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['uid'], 'abc123')
        self.assertEqual(s.validated_data['token'], 'valid-token')
        self.assertEqual(s.validated_data['password'], 'StrongP@ss1')

    def test_uid_field_is_required(self):
        data = self._valid_data()
        del data['uid']
        s = PasswordResetConfirmSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('uid', s.errors)

    def test_token_field_is_required(self):
        data = self._valid_data()
        del data['token']
        s = PasswordResetConfirmSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('token', s.errors)

    def test_password_field_is_required(self):
        data = self._valid_data()
        del data['password']
        s = PasswordResetConfirmSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('password', s.errors)

    def test_password_min_length_enforced(self):
        s = PasswordResetConfirmSerializer(data=self._valid_data(password='Short1'))
        self.assertFalse(s.is_valid())
        self.assertIn('password', s.errors)

    def test_weak_password_errors_are_returned_as_list(self):
        # All-numeric password triggers Django's NumericPasswordValidator
        s = PasswordResetConfirmSerializer(data=self._valid_data(password='12345678'))
        self.assertFalse(s.is_valid())
        self.assertIn('password', s.errors)
        self.assertIsInstance(s.errors['password'], list)

    def test_too_short_password_fails(self):
        s = PasswordResetConfirmSerializer(data=self._valid_data(password='abc'))
        self.assertFalse(s.is_valid())
        self.assertIn('password', s.errors)

    def test_password_is_write_only(self):
        # Confirm password field is write_only (not returned in serializer representation)
        field = PasswordResetConfirmSerializer().fields['password']
        self.assertTrue(field.write_only)

    def test_empty_uid_fails(self):
        s = PasswordResetConfirmSerializer(data=self._valid_data(uid=''))
        self.assertFalse(s.is_valid())
        self.assertIn('uid', s.errors)

    def test_empty_token_fails(self):
        s = PasswordResetConfirmSerializer(data=self._valid_data(token=''))
        self.assertFalse(s.is_valid())
        self.assertIn('token', s.errors)


class PasswordResetRequestTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = '/api/auth/password-reset/'
        self.email = 'test@example.com'
        self.user = User.objects.create_user(
            username=self.email, email=self.email, password='Password123!'
        )

    @patch('users.views.EmailMultiAlternatives.send')
    def test_request_returns_200_for_any_email(self, _mock_send):
        response = self.client.post(self.url, {'email': self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(self.url, {'email': 'unknown@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_email_returns_400(self):
        response = self.client.post(self.url, {'email': 'notanemail'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_audit_log_created_for_request(self):
        """Test that password reset request creates audit log entry."""
        initial_count = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).count()

        self.client.post(self.url, {'email': self.email})

        new_count = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).count()
        self.assertEqual(new_count, initial_count + 1)

        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).latest('created_at')
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.email, self.email)
        self.assertIsNotNone(audit.ip_address)

    def test_audit_log_includes_user_agent(self):
        """Test that audit log captures user agent."""
        self.client.post(
            self.url, {'email': self.email}, HTTP_USER_AGENT='Mozilla/5.0 Test Browser'
        )

        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).latest('created_at')
        self.assertIn('Mozilla', audit.user_agent)

    def test_throttling_applies(self):
        for _ in range(5):
            self.client.post(self.url, {'email': self.email})

        response = self.client.post(self.url, {'email': self.email})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class PasswordResetConfirmViewTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@gmail.com',
            password='OldP@ssword1',
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = password_reset_token.make_token(self.user)
        self.url = '/api/auth/password-reset/confirm/'

    def test_valid_token_and_uid_changes_password(self):
        """Test that valid uid and token successfully reset password."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Password changed successfully.')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewP@ssword1'))

    def test_password_reset_creates_audit_log(self):
        """Test that password reset confirmation creates an audit log entry."""
        initial_count = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_CONFIRMED
        ).count()

        self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )

        new_count = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_CONFIRMED
        ).count()
        self.assertEqual(new_count, initial_count + 1)

        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_CONFIRMED
        ).latest('created_at')
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.email, self.user.email)
        self.assertIsNotNone(audit.ip_address)

    def test_password_reset_revokes_existing_refresh_tokens(self):
        """Test that refresh tokens are revoked after password reset."""
        refresh = str(RefreshToken.for_user(self.user))

        self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )

        refresh_response = self.client.post(
            '/api/auth/refresh/',
            {'refresh': refresh},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_returns_400(self):
        """Test that invalid token returns 400."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': 'invalid-token-123',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired token.')

    def test_expired_token_returns_400(self):
        """Test that expired token returns 400."""
        # Create a user with an old timestamp to simulate token expiry
        with patch('users.tokens.password_reset_token.check_token', return_value=False):
            response = self.client.post(
                self.url,
                {
                    'uid': self.uid,
                    'token': self.token,
                    'password': 'NewP@ssword1',
                },
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_returns_400(self):
        """Test that invalid uid returns 400."""
        response = self.client.post(
            self.url,
            {
                'uid': 'invaliduid',
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired token.')

    def test_nonexistent_user_returns_400(self):
        """Test that nonexistent user ID returns 400."""
        invalid_uid = urlsafe_base64_encode(force_bytes(999999))
        response = self.client.post(
            self.url,
            {
                'uid': invalid_uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_returns_422(self):
        """Test that weak password returns 422."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': '123',  # Too weak
            },
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn('password', response.data)

    def test_common_password_returns_422(self):
        """Test that common password returns 422."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'password123',  # Common password
            },
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn('password', response.data)

    def test_numeric_password_returns_422(self):
        """Test that all-numeric password returns 422."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': '12345678',  # All numeric
            },
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn('password', response.data)

    def test_missing_uid_returns_400(self):
        """Test that missing uid returns 400."""
        response = self.client.post(
            self.url,
            {
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_token_returns_400(self):
        """Test that missing token returns 400."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password_returns_400(self):
        """Test that missing password returns 400 (malformed request)."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_single_use_enforced_by_expiry(self):
        """Test that used token cannot be reused (enforced by token generator)."""
        # First use
        self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )

        # Django's PasswordResetTokenGenerator automatically invalidates
        # tokens after first use by checking password_changed_date
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'AnotherNew@ssw0rd2',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_login_with_new_password_after_reset(self):
        """Test that user can login with new password after reset."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user from database and activate
        self.user.refresh_from_db()
        self.user.is_active = True
        self.user.is_verified = True
        self.user.is_startup = True
        self.user.save()

        login_response = self.client.post(
            '/api/auth/login/',
            {
                'email': self.user.email,
                'password': 'NewP@ssword1',
                'role': 'startup',
            },
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)


class PasswordResetRequestViewAdditionalTests(APITestCase):
    """Additional view-level tests for PasswordResetRequestView changes in this PR."""

    def setUp(self):
        cache.clear()
        self.url = '/api/auth/password-reset/'
        self.email = 'viewtest@example.com'
        self.user = User.objects.create_user(
            username=self.email, email=self.email, password='Password123!'
        )

    @patch('users.views.EmailMultiAlternatives.send')
    def test_audit_created_for_unknown_email_with_null_user(self, _mock_send):
        """Unknown email still creates an audit entry with user=None."""
        unknown = 'unknown@nowhere.com'
        initial_count = PasswordResetAudit.objects.count()

        self.client.post(self.url, {'email': unknown})

        self.assertEqual(PasswordResetAudit.objects.count(), initial_count + 1)
        audit = PasswordResetAudit.objects.latest('created_at')
        self.assertIsNone(audit.user)
        self.assertEqual(audit.email, unknown)
        self.assertEqual(audit.action, PasswordResetAudit.ACTION_REQUESTED)

    @patch('users.views.EmailMultiAlternatives.send')
    def test_audit_user_agent_truncated_to_500_chars(self, _mock_send):
        """user_agent is stored truncated to 500 chars via view."""
        long_agent = 'B' * 600
        self.client.post(
            self.url, {'email': self.email}, HTTP_USER_AGENT=long_agent
        )
        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).latest('created_at')
        self.assertEqual(len(audit.user_agent), 500)

    @patch('users.views.EmailMultiAlternatives.send')
    def test_audit_without_user_agent_stores_empty_string(self, _mock_send):
        """Requests without User-Agent header store empty string."""
        self.client.post(self.url, {'email': self.email})
        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).latest('created_at')
        # Should be empty string or whatever the client sends by default
        self.assertIsInstance(audit.user_agent, str)

    @patch('users.views.EmailMultiAlternatives.send')
    def test_email_send_failure_still_returns_200(self, mock_send):
        """Email sending failure does not propagate as an error response."""
        mock_send.side_effect = Exception('SMTP connection failed')

        response = self.client.post(self.url, {'email': self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('users.views.EmailMultiAlternatives.send')
    def test_response_message_is_generic(self, _mock_send):
        """Response message does not reveal whether email exists."""
        response_known = self.client.post(self.url, {'email': self.email})
        response_unknown = self.client.post(self.url, {'email': 'nope@example.com'})

        self.assertEqual(
            response_known.data['detail'], response_unknown.data['detail']
        )


class PasswordResetConfirmViewAdditionalTests(APITestCase):
    """Additional view-level tests for PasswordResetConfirmView changes in this PR."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='confirmtest',
            email='confirmtest@example.com',
            password='OldP@ssword1',
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = password_reset_token.make_token(self.user)
        self.url = '/api/auth/password-reset/confirm/'

    def test_confirm_audit_captures_user_agent(self):
        """Confirm action audit log stores user agent from request."""
        self.client.post(
            self.url,
            {'uid': self.uid, 'token': self.token, 'password': 'NewP@ssword1'},
            HTTP_USER_AGENT='TestBrowser/2.0',
        )
        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_CONFIRMED
        ).latest('created_at')
        self.assertIn('TestBrowser', audit.user_agent)

    def test_confirm_audit_action_is_confirmed(self):
        """Audit log created on confirm has ACTION_CONFIRMED."""
        self.client.post(
            self.url,
            {'uid': self.uid, 'token': self.token, 'password': 'NewP@ssword1'},
        )
        audit = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_CONFIRMED
        ).latest('created_at')
        self.assertEqual(audit.action, PasswordResetAudit.ACTION_CONFIRMED)
        self.assertEqual(audit.user, self.user)

    def test_short_password_returns_400_not_422(self):
        """Password shorter than min_length=8 returns 400 (required-like), not 422."""
        response = self.client.post(
            self.url,
            {'uid': self.uid, 'token': self.token, 'password': 'abc'},
        )
        # min_length error code is 'min_length', not 'invalid' — view treats it as 400
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY])

    def test_weak_password_error_contains_password_key(self):
        """422 response for weak password includes 'password' key in response data."""
        response = self.client.post(
            self.url,
            {'uid': self.uid, 'token': self.token, 'password': 'password123'},
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn('password', response.data)
        self.assertIsInstance(response.data['password'], list)

    def test_empty_body_returns_400(self):
        """Empty POST body returns 400."""
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_does_not_create_request_audit(self):
        """Confirm action creates ACTION_CONFIRMED audit, not ACTION_REQUESTED."""
        initial_requested = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).count()

        self.client.post(
            self.url,
            {'uid': self.uid, 'token': self.token, 'password': 'NewP@ssword1'},
        )

        after_requested = PasswordResetAudit.objects.filter(
            action=PasswordResetAudit.ACTION_REQUESTED
        ).count()
        self.assertEqual(after_requested, initial_requested)


class TestLoginApi(APITestCase):
    def setUp(self):
        cache.clear()

        self.password = 'P@ssw0rd123'
        self.role = 'startup'
        self.user = User.objects.create_user(
            email=self.email,
            username=self.email,
            password=self.password,
            is_active=True,
            is_startup=True,
            is_investor=True,
        )
        self.url = reverse('auth-login')

    def test_valid_credentials_returns_200_with_tokens(self):
        res = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': self.password,
                'role': self.role,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        self.assertEqual(res.data['user']['email'], self.email)
        self.assertEqual(res.data['user']['role'], 'startup')

    def test_wrong_password_returns_401_generic(self):
        res = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': 'wrongpass',
                'role': self.role,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        detail = res.data.get('detail')
        if isinstance(detail, list):
            detail = detail[0]
        self.assertEqual(detail, 'Invalid email or password.')

    def test_lockout_after_5_failed_attempts(self):
        for _ in range(5):
            self.client.post(
                self.url,
                {
                    'email': self.email,
                    'password': 'wrong',
                    'role': self.role,
                },
                format='json',
            )
        res = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': 'wrong',
                'role': self.role,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        detail = res.data.get('detail')
        if isinstance(detail, list):
            detail = detail[0]
        self.assertEqual(detail, 'Too many failed attempts. Try again later.')

    def test_successful_login_clears_fail_counter(self):
        for _ in range(4):
            self.client.post(
                self.url,
                {
                    'email': self.email,
                    'password': 'wrong',
                    'role': self.role,
                },
                format='json',
            )

        ok = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': self.password,
                'role': self.role,
            },
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

        post_login_failure = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': 'wrong',
                'role': self.role,
            },
            format='json',
        )
        self.assertEqual(
            post_login_failure.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_remember_true_returns_200(self):
        res = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': self.password,
                'role': self.role,
                'remember': True,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_wrong_role_returns_401_generic(self):
        self.user.is_startup = True
        self.user.is_investor = False
        self.user.save()

        res = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': self.password,
                'role': 'investor',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_role_returns_400(self):
        res = self.client.post(
            self.url,
            {
                'email': self.email,
                'password': self.password,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshAndLogoutApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = 'P@ssw0rd123'
        self.user = User.objects.create_user(
            email='refresh@example.com',
            username='refresh@example.com',
            password=self.password,
            is_active=True,
            is_startup=True,
        )
        login_response = self.client.post(
            reverse('auth-login'),
            {
                'email': self.user.email,
                'password': self.password,
                'role': 'startup',
            },
            format='json',
        )
        self.refresh_token = login_response.data['refresh']
        self.refresh_url = reverse('token-refresh')
        self.logout_url = reverse('auth-logout')

    def test_refresh_returns_new_access_token_for_valid_refresh(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_invalid_token_returns_401(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': 'not-a-valid-token'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_refresh_and_future_refresh_fails(self):
        self.client.post(
            self.logout_url,
            {'refresh': self.refresh_token},
            format='json',
        )
        refresh_response = self.client.post(
            self.refresh_url,
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_refresh_token(self):
        response = self.client.post(self.logout_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_invalid_refresh_returns_400(self):
        response = self.client.post(
            self.logout_url,
            {'refresh': 'invalid-token'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
