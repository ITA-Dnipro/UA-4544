from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from projects.models import Project
from rest_framework import status
from rest_framework.test import APITestCase

from startups.models import StartupProfile

User = get_user_model()


def _make_user(username, email, **kwargs):
    defaults = {
        'password': '123qwe!@#',
        'is_startup': True,
        'is_investor': False,
        'is_verified': True,
    }
    defaults.update(kwargs)
    return User.objects.create_user(username=username, email=email, **defaults)


def _make_startup(user, **kwargs):
    defaults = {
        'company_name': 'Test Company',
        'description': 'This is a test company.',
        'website': 'https://www.testcompany.com',
    }
    defaults.update(kwargs)
    return StartupProfile.objects.create(user=user, **defaults)


def _make_project(startup, **kwargs):
    defaults = {
        'title': 'Test Project',
        'status': 'idea',
        'short_description': 'A short desc.',
        'description': 'Full description.',
        'target_amount': 100000,
    }
    defaults.update(kwargs)
    return Project.objects.create(startup=startup, **defaults)


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


class SlugAutoGenerationTests(TestCase):
    def test_two_profiles_without_slug_do_not_collide(self):
        """Regression: creating profiles without a slug must not raise IntegrityError."""
        user1 = _make_user('user1', 'user1@example.com')
        user2 = _make_user('user2', 'user2@example.com')

        profile1 = _make_startup(user1, company_name='Acme Corp')
        profile2 = _make_startup(user2, company_name='Acme Corp')

        self.assertIsNotNone(profile1.slug)
        self.assertIsNotNone(profile2.slug)
        self.assertNotEqual(profile1.slug, profile2.slug)


class StartupProjectListAPITests(TestCase):
    """Tests for GET /api/startups/{id}/projects/"""

    def setUp(self):
        self.user = _make_user('projuser', 'proj@example.com')
        self.startup = _make_startup(self.user, company_name='Projects Corp')
        self.url = reverse('startup-projects', kwargs={'pk': self.startup.pk})

    def _url(self, startup_pk):
        return reverse('startup-projects', kwargs={'pk': startup_pk})

    def test_returns_200_and_expected_envelope(self):
        _make_project(self.startup, title='Alpha')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)

    def test_result_contains_expected_card_fields(self):
        _make_project(
            self.startup,
            title='Handmade Chairs',
            status='idea',
            short_description='Fine woodwork.',
        )
        response = self.client.get(self.url)
        card = response.json()['results'][0]

        self.assertIn('id', card)
        self.assertEqual(card['title'], 'Handmade Chairs')
        self.assertEqual(card['status'], 'active')
        self.assertIn('thumbnail', card)
        self.assertEqual(card['short_description'], 'Fine woodwork.')

    def test_inactive_project_status_string(self):
        _make_project(self.startup, title='Dormant', status='closed')
        response = self.client.get(self.url)
        card = response.json()['results'][0]

        self.assertEqual(card['status'], 'inactive')

    def test_count_reflects_total_projects(self):
        for i in range(4):
            _make_project(self.startup, title=f'Project {i}')
        response = self.client.get(self.url)

        self.assertEqual(response.json()['count'], 4)

    def test_default_page_size_is_six(self):
        for i in range(8):
            _make_project(self.startup, title=f'Project {i}')
        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data['count'], 8)
        self.assertEqual(len(data['results']), 6)

    def test_page_size_query_param_is_respected(self):
        for i in range(8):
            _make_project(self.startup, title=f'Project {i}')
        response = self.client.get(self.url + '?page_size=3')
        data = response.json()

        self.assertEqual(len(data['results']), 3)

    def test_max_page_size_is_respected(self):
        for i in range(105):
            _make_project(self.startup, title=f'Project {i}')
        response = self.client.get(self.url + '?page_size=500')
        data = response.json()

        self.assertEqual(len(data['results']), 100)

    def test_second_page_returns_remaining_items(self):
        for i in range(8):
            _make_project(self.startup, title=f'Project {i}')
        response = self.client.get(self.url + '?page=2&page_size=6')
        data = response.json()

        self.assertEqual(len(data['results']), 2)

    def test_status_filter_active(self):
        _make_project(self.startup, title='Active One', status='idea')
        _make_project(self.startup, title='Inactive One', status='closed')
        response = self.client.get(self.url + '?status=active')
        data = response.json()

        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['title'], 'Active One')

    def test_status_filter_inactive(self):
        _make_project(self.startup, title='Active One', status='idea')
        _make_project(self.startup, title='Inactive One', status='closed')
        response = self.client.get(self.url + '?status=inactive')
        data = response.json()

        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['title'], 'Inactive One')

    def test_returns_only_projects_for_given_startup(self):
        """Projects from another startup must not appear in the response."""
        other_user = _make_user('other', 'other@example.com')
        other_startup = _make_startup(other_user, company_name='Other Corp')
        _make_project(self.startup, title='Mine')
        _make_project(other_startup, title='Not Mine')

        response = self.client.get(self.url)
        titles = [r['title'] for r in response.json()['results']]

        self.assertIn('Mine', titles)
        self.assertNotIn('Not Mine', titles)

    def test_returns_empty_list_for_startup_with_no_projects(self):
        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])

    def test_returns_404_for_unknown_startup(self):
        response = self.client.get(self._url(99999))

        self.assertEqual(response.status_code, 404)

    def test_invalid_status_param_is_ignored(self):
        """An unrecognised ?status value must not filter the queryset."""
        _make_project(self.startup, title='Active One', status='idea')
        _make_project(self.startup, title='Inactive One', status='closed')
        response = self.client.get(self.url + '?status=abc')
        data = response.json()

        self.assertEqual(data['count'], 2)


class PublishProfilePermissionTests(APITestCase):
    def setUp(self):
        self.owner = _make_user('owner', 'owner@test.com')
        self.profile = StartupProfile.objects.create(
            user=self.owner,
            company_name='Test Startup',
            description='A great startup description.',
            contact_email='contact@test.com',
        )

        self.stranger = _make_user('stranger', 'stranger@test.com')

        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
        )

        self.url = reverse('startup-publish', kwargs={'pk': self.profile.pk})

    def test_anonymous_cannot_publish(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_cannot_publish(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_publish(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_incomplete_profile_returns_400(self):
        self.profile.description = ''
        self.profile.save()

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('missing_fields', response.data)
        self.assertIn('description', response.data['missing_fields'])

    def test_owner_complete_profile_publishes(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_published)
        self.assertIsNotNone(self.profile.published_at)
        self.assertEqual(self.profile.published_by, self.owner)

    def test_publish_already_published_returns_200(self):
        self.profile.is_published = True
        self.profile.save()

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Profile is already published.')
