from django.test import TestCase

from users.models import User


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
