from django.test import TestCase
from users.models import User

from startups.models import StartupProfile



class StartupProfileModelTests(TestCase):
    def test_startup_profile_creation(self):
        user = User.objects.create_user(
            username='startupuser',
            email='startup@example.com',
            password='123qwe!@#',
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        startup_profile = StartupProfile.objects.create(
            user=user,
            company_name='Test Company',
            description='This is a test company.',
            website='https://www.testcompany.com',
        )

        self.assertEqual(startup_profile.user, user)
        self.assertEqual(startup_profile.company_name, 'Test Company')
        self.assertEqual(startup_profile.description, 'This is a test company.')
        self.assertEqual(startup_profile.website, 'https://www.testcompany.com')
