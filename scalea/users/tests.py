from unittest.mock import patch

from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from users.tokens import password_reset_token


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


class PasswordResetRequestViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@gmail.com",
            password="OldP@ssword1",
        )
        self.url = "/api/auth/password-reset/"

    @patch("users.views.auth.EmailMultiAlternatives.send")
    def test_returns_200_if_email_exists(self, _mock_send):
        response = self.client.post(self.url, {"email": "test@gmail.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_returns_200_if_email_not_exists(self):
        response = self.client.post(self.url, {"email": "nobody@gmail.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_email_returns_400(self):
        response = self.client.post(self.url, {"email": "notanemail"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser2",
            email="test@gmail.com",
            password="OldP@ssword1",
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = password_reset_token.make_token(self.user)
        self.url = "/api/auth/password-reset/confirm/"

    def test_valid_token_changes_password(self):
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
                "password": "NewP@ssword1",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewP@ssword1"))

    def test_invalid_token_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": "invalid-token-123",
                "password": "NewP@ssword1",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "uid": "invaliduid",
                "token": self.token,
                "password": "NewP@ssword1",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
