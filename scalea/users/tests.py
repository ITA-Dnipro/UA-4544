from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from investors.models import InvestorProfile
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from startups.models import StartupProfile

from users.models import PasswordResetAuditLog, PasswordResetToken
from users.tokens import hash_token, password_reset_token

User = get_user_model()


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

class PasswordResetRequestViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@gmail.com',
            password='OldP@ssword1',
        )
        self.url = '/api/auth/password-reset/'

    @patch('users.views.EmailMultiAlternatives.send')
    def test_returns_200_if_email_exists(self, _mock_send):
        response = self.client.post(self.url, {'email': 'test@gmail.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_returns_200_if_email_not_exists(self):
        response = self.client.post(self.url, {'email': 'nobody@gmail.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_email_returns_400(self):
        response = self.client.post(self.url, {'email': 'notanemail'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2',
            email='test@gmail.com',
            password='OldP@ssword1',
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = password_reset_token.make_token(self.user)
        self.token_hash = hash_token(self.token)
        self.combined_token = f'{self.uid}.{self.token}'
        self.url = '/api/auth/password-reset/confirm/'

        # Create token record for single-use tracking
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash=self.token_hash,
            is_used=False,
        )

    def test_valid_token_changes_password(self):
        """Test that a valid token successfully resets the password."""
        response = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Password changed successfully.')
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewP@ssword1'))

    def test_valid_token_logs_audit_entry(self):
        """Test that a successful password reset logs an audit entry."""
        response = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that an audit log was created
        audit_log = PasswordResetAuditLog.objects.filter(
            user=self.user,
            action='confirm',
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details.get('success'), True)
        self.assertIsNotNone(audit_log.ip_address)
        self.assertIsNotNone(audit_log.user_agent)

    def test_invalid_token_returns_400(self):
        """Test that an invalid token returns 400."""
        response = self.client.post(
            self.url,
            {
                'token': f'{self.uid}.invalid-token-123',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired token.')

    def test_invalid_token_logs_failed_audit_entry(self):
        """Test that an invalid token attempt logs a failed audit entry."""
        response = self.client.post(
            self.url,
            {
                'token': f'{self.uid}.invalid-token-123',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check that a failed audit log was created
        audit_log = PasswordResetAuditLog.objects.filter(
            user=self.user,
            action='failed',
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details.get('reason'), 'invalid_or_expired_token')

    def test_invalid_uid_returns_400(self):
        """Test that an invalid uid returns 400."""
        response = self.client.post(
            self.url,
            {
                'token': f'invaliduid.{self.token}',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired token.')

    def test_weak_password_returns_422(self):
        """Test that a weak password returns 422."""
        response = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': 'weak',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn('password', response.data)

    def test_token_single_use_enforcement(self):
        """Test that a token can only be used once."""
        new_password = 'NewP@ssword1'
        
        # First use should succeed
        response1 = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': new_password,
            },
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Mark token as used
        token_record = PasswordResetToken.objects.get(token_hash=self.token_hash)
        self.assertTrue(token_record.is_used)
        
        # Second use should fail
        response2 = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': 'AnotherPassword123!',
            },
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.data['detail'], 'Invalid or expired token.')

    def test_separate_uid_and_token_format(self):
        """Test that uid and token can be provided separately."""
        response = self.client.post(
            self.url,
            {
                'uid': self.uid,
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewP@ssword1'))

    def test_missing_uid_in_separate_format_returns_400(self):
        """Test that missing uid in separate format returns 400."""
        response = self.client.post(
            self.url,
            {
                'token': self.token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_token_returns_400(self):
        """Test that an expired token returns 400."""
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        
        # Create a token and then test with a different user to simulate expiry
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@gmail.com',
            password='OldP@ssword1',
        )
        
        # Use the first user's token with the second user's uid
        other_uid = urlsafe_base64_encode(force_bytes(other_user.pk))
        combined_token = f'{other_uid}.{self.token}'
        
        response = self.client.post(
            self.url,
            {
                'token': combined_token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_response_message_format_success(self):
        """Test that the success response has the correct format."""
        response = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Password changed successfully.')

    def test_response_message_format_error(self):
        """Test that the error response has the correct format."""
        response = self.client.post(
            self.url,
            {
                'token': f'{self.uid}.invalid-token-123',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Invalid or expired token.')