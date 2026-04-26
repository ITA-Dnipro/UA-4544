from django.test import TestCase
from django.urls import reverse

from startups.models import StartupProfile
from users.models import User


def _make_user(username, email, **kwargs):
    return User.objects.create_user(
        username=username,
        email=email,
        password='123qwe!@#',
        is_startup=True,
        is_investor=False,
        is_verified=True,
        **kwargs,
    )


def _make_startup(user, **kwargs):
    defaults = {
        'company_name': 'Test Company',
        'description': 'This is a test company.',
        'website': 'https://www.testcompany.com',
    }
    defaults.update(kwargs)
    return StartupProfile.objects.create(user=user, **defaults)


class StartupProfileModelTests(TestCase):
    def test_startup_profile_creation(self):
        user = _make_user('startupuser', 'startup@example.com')
        startup_profile = _make_startup(user)

        self.assertEqual(startup_profile.user, user)
        self.assertEqual(startup_profile.company_name, 'Test Company')
        self.assertEqual(startup_profile.description, 'This is a test company.')
        self.assertEqual(startup_profile.website, 'https://www.testcompany.com')


class StartupPublicProfileAPITests(TestCase):
    def setUp(self):
        self.user = _make_user('apiuser', 'api@example.com')
        self.startup = _make_startup(
            self.user,
            company_name='Handmade Co',
            slug='handmade-co',
            short_description='Woodwork & ceramics',
            description='Full about text.',
            contact_email='info@handmade.co',
            contact_phone='+380123456789',
            tags=['craft', 'pottery'],
            website='https://handmade.example',
        )
        self.url = reverse('startup-public-profile', kwargs={'pk': self.startup.pk})

    def test_returns_200_with_expected_schema(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['id'], self.startup.pk)
        self.assertEqual(data['company_name'], 'Handmade Co')
        self.assertEqual(data['slug'], 'handmade-co')
        self.assertEqual(data['short_description'], 'Woodwork & ceramics')
        self.assertIn('<p>', data['about_html'])
        self.assertIn('Full about text.', data['about_html'])
        self.assertEqual(data['contact']['email'], 'info@handmade.co')
        self.assertEqual(data['contact']['phone'], '+380123456789')
        self.assertEqual(data['website'], 'https://handmade.example')
        self.assertEqual(data['tags'], ['craft', 'pottery'])
        self.assertEqual(data['followers_count'], 0)
        self.assertEqual(data['projects_count'], 0)
        self.assertIn('created_at', data)

    def test_returns_404_for_unknown_id(self):
        url = reverse('startup-public-profile', kwargs={'pk': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
