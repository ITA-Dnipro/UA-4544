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

from users.tokens import password_reset_token

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
        self.combined_token = f'{self.uid}.{self.token}'
        self.url = '/api/auth/password-reset/confirm/'

    def test_valid_token_changes_password(self):
        response = self.client.post(
            self.url,
            {
                'token': self.combined_token,
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewP@ssword1'))

    def test_invalid_token_returns_400(self):
        response = self.client.post(
            self.url,
            {
                'token': f'{self.uid}.invalid-token-123',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_returns_400(self):
        response = self.client.post(
            self.url,
            {
                'token': f'invaliduid.{self.token}',
                'password': 'NewP@ssword1',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
