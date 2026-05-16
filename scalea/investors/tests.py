from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from investors.models import InvestorProfile, SavedItem, SavedStartup
from investors.serializers import SavedItemCardSerializer
from projects.models import Project, ProjectVisibility
from startups.models import StartupProfile

User = get_user_model()


class InvestorProfileModelTests(TestCase):
    def test_investor_profile_creation(self):
        user = User.objects.create_user(
            username='investoruser',
            email='investor@example.com',
            password='123qwe!@#',
            is_startup=False,
            is_investor=True,
            is_verified=True,
        )

        investor_profile = InvestorProfile.objects.create(
            user=user,
            company_name='Investor Company',
            bio='Angel investor',
            investment_focus='AI, SaaS',
            website='https://www.investorcompany.com',
        )

        self.assertEqual(investor_profile.user, user)
        self.assertEqual(investor_profile.company_name, 'Investor Company')
        self.assertEqual(investor_profile.bio, 'Angel investor')
        self.assertEqual(investor_profile.investment_focus, 'AI, SaaS')
        self.assertEqual(investor_profile.website, 'https://www.investorcompany.com')


class SavedStartupModelTests(TestCase):
    def test_saved_startup_creation(self):
        investor_user = User.objects.create_user(
            username='investoruser',
            email='investor@example.com',
            password='123qwe!@#',
            is_startup=False,
            is_investor=True,
            is_verified=True,
        )

        startup_user = User.objects.create_user(
            username='startupuser',
            email='startup@example.com',
            password='123qwe!@#',
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        investor_profile = InvestorProfile.objects.create(
            user=investor_user,
            company_name='Investor Company',
            bio='Angel investor',
            investment_focus='AI, SaaS',
            website='https://www.investorcompany.com',
        )

        startup_profile = StartupProfile.objects.create(
            user=startup_user,
            company_name='Test Company',
            description='This is a test company.',
            website='https://www.testcompany.com',
        )

        saved_startup = SavedStartup.objects.create(
            investor_profile=investor_profile,
            startup_profile=startup_profile,
        )

        self.assertEqual(saved_startup.investor_profile, investor_profile)
        self.assertEqual(saved_startup.startup_profile, startup_profile)


class InvestorProfileAPITests(APITestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(
            username='investor_owner',
            email='owner@investor.com',
            password='password123',
            is_investor=True,
            is_startup=False,
        )

        self.profile = InvestorProfile.objects.create(
            user=self.owner_user,
            company_name='Alpha VC',
            bio='Early-stage tech focus.',
            investment_focus='AI, Web3',
            website='https://alpha-vc.com',
        )

        self.stranger_user = User.objects.create_user(
            username='stranger_user',
            email='stranger@test.com',
            password='password123',
            is_investor=True,
        )

        self.url = reverse('profile-detail', kwargs={'pk': self.owner_user.pk})

    def test_get_investor_profile_public_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Alpha VC')
        self.assertEqual(response.data['website'], 'https://alpha-vc.com')
        self.assertIn('investments_count', response.data)
        self.assertIn('saved_startups_count', response.data)

    def test_owner_can_patch_investor_profile(self):
        self.client.force_authenticate(user=self.owner_user)
        payload = {'company_name': 'Updated Alpha VC'}

        response = self.client.patch(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Updated Alpha VC')

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.company_name, 'Updated Alpha VC')

    def test_owner_can_put_investor_profile(self):
        self.client.force_authenticate(user=self.owner_user)
        payload = {
            'company_name': 'New Fund Name',
            'bio': 'New bio description',
            'investment_focus': 'SaaS only',
            'website': 'https://newfund.com',
        }

        response = self.client.put(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['investment_focus'], 'SaaS only')

    def test_stranger_cannot_update_investor_profile(self):
        self.client.force_authenticate(user=self.stranger_user)
        response = self.client.patch(self.url, {'company_name': 'Hacker Capital'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_update_investor_profile(self):
        response = self.client.patch(self.url, {'company_name': 'Anonymous VC'})
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_update_invalid_data_returns_400(self):
        self.client.force_authenticate(user=self.owner_user)
        payload = {'website': 'not-a-url'}

        response = self.client.patch(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('website', response.data)

    def test_get_non_existent_user_returns_404(self):
        invalid_url = reverse('profile-detail', kwargs={'pk': 9999})
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SavedItemAPITests(APITestCase):
    def setUp(self):
        self.investor_user = User.objects.create_user(
            username='investor@test.com',
            email='investor@test.com',
            password='Password123!',
            is_investor=True,
            is_active=True,
        )
        self.investor_profile = InvestorProfile.objects.create(
            user=self.investor_user,
            company_name='Test VC',
        )
        startup_user = User.objects.create_user(
            username='startup@test.com',
            email='startup@test.com',
            password='Password123!',
            is_startup=True,
            is_active=True,
        )
        self.startup = StartupProfile.objects.create(
            user=startup_user,
            company_name='Test Startup',
        )
        self.url = f'/api/users/{self.investor_user.id}/saved/'

    def test_create_saved_item_returns_201(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {'target_type': 'startup', 'target_id': str(self.startup.pk)}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('saved_id', response.data)
        self.assertIn('saved_at', response.data)

    def test_create_duplicate_is_idempotent_returns_200(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {'target_type': 'startup', 'target_id': str(self.startup.pk)}
        response1 = self.client.post(self.url, payload, format='json')
        response2 = self.client.post(self.url, payload, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data['saved_id'], response2.data['saved_id'])
        self.assertEqual(
            SavedItem.objects.filter(investor=self.investor_profile).count(), 1
        )

    def test_create_invalid_target_id_returns_404(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {'target_type': 'startup', 'target_id': '99999'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_invalid_target_type_returns_400(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {'target_type': 'banana', 'target_id': '1'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_unauthenticated_returns_401(self):
        payload = {'target_type': 'startup', 'target_id': str(self.startup.pk)}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_non_investor_returns_403(self):
        startup_user = User.objects.create_user(
            username='startup2@test.com',
            email='startup2@test.com',
            password='Password123!',
            is_startup=True,
            is_investor=False,
            is_active=True,
        )
        self.client.force_authenticate(user=startup_user)
        url = f'/api/users/{startup_user.id}/saved/'
        payload = {'target_type': 'startup', 'target_id': str(self.startup.pk)}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_wrong_user_id_returns_403(self):
        other_user = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='Password123!',
            is_investor=True,
            is_active=True,
        )
        self.client.force_authenticate(user=self.investor_user)
        url = f'/api/users/{other_user.id}/saved/'
        payload = {'target_type': 'startup', 'target_id': str(self.startup.pk)}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_saved_item_returns_204(self):
        self.client.force_authenticate(user=self.investor_user)
        saved_item = SavedItem.objects.create(
            investor=self.investor_profile,
            target_type='startup',
            target_id=str(self.startup.pk),
        )
        url = f'/api/users/{self.investor_user.id}/saved/{saved_item.pk}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SavedItem.objects.filter(pk=saved_item.pk).exists())

    def test_delete_nonexistent_returns_404(self):
        self.client.force_authenticate(user=self.investor_user)
        url = f'/api/users/{self.investor_user.id}/saved/99999/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_wrong_user_returns_403(self):
        other_investor_user = User.objects.create_user(
            username='other_inv@test.com',
            email='other_inv@test.com',
            password='Password123!',
            is_investor=True,
            is_active=True,
        )
        other_investor_profile = InvestorProfile.objects.create(
            user=other_investor_user,
            company_name='Other VC',
        )
        saved_item = SavedItem.objects.create(
            investor=other_investor_profile,
            target_type='startup',
            target_id=str(self.startup.pk),
        )
        self.client.force_authenticate(user=self.investor_user)
        url = f'/api/users/{other_investor_user.id}/saved/{saved_item.pk}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SavedItemCardSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            username='investor',
            email='inv@t.com',
            password='123',
            is_investor=True,
        )
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            company_name='VC',
        )

        self.startup_user = User.objects.create_user(
            username='startup',
            email='s@t.com',
            password='123',
            is_startup=True,
        )
        self.startup = StartupProfile.objects.create(
            user=self.startup_user,
            company_name='Test Startup',
            logo_url='http://logo',
            short_description='desc',
            tags=['tag1', 'tag2'],
            description='desc',
            website='https://test.com',
        )

        self.project = Project.objects.create(
            startup=self.startup,
            title='Test Project',
            slug='test-project',
            short_description='Project desc',
            description='Full project description',
            target_amount=1000,
            currency='UAH',
            visibility=ProjectVisibility.PUBLIC,
        )

    def serialize(self, saved, user=None):
        request = self.factory.get('/api/users/1/saved/')
        request.user = user or self.user

        return SavedItemCardSerializer(
            saved,
            context={'request': request},
        ).data

    def test_startup_card_fields(self):
        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='startup',
            target_id=self.startup.pk,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(self.startup.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'startup')
        self.assertEqual(data['title'], self.startup.company_name)
        self.assertEqual(data['slug'], self.startup.slug)
        self.assertEqual(data['thumbnail_url'], self.startup.logo_url)
        self.assertEqual(data['short_description'], self.startup.short_description)
        self.assertEqual(data['tags'], self.startup.tags)
        self.assertTrue(data['is_available'])
        self.assertIsNone(data['unavailable_reason'])

    def test_company_card_fields(self):
        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='company',
            target_id=self.startup.pk,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(self.startup.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'company')
        self.assertEqual(data['title'], self.startup.company_name)
        self.assertEqual(data['slug'], self.startup.slug)
        self.assertEqual(data['thumbnail_url'], self.startup.logo_url)
        self.assertEqual(data['short_description'], self.startup.short_description)
        self.assertEqual(data['tags'], self.startup.tags)
        self.assertTrue(data['is_available'])
        self.assertIsNone(data['unavailable_reason'])

    def test_project_public_card_fields(self):
        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='project',
            target_id=self.project.pk,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(self.project.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'project')
        self.assertEqual(data['title'], self.project.title)
        self.assertEqual(data['slug'], self.project.slug)
        self.assertIsNone(data['thumbnail_url'])
        self.assertEqual(data['short_description'], self.project.short_description)
        self.assertEqual(data['tags'], [])
        self.assertTrue(data['is_available'])
        self.assertIsNone(data['unavailable_reason'])

    def test_project_private_card_fields(self):
        self.project.visibility = ProjectVisibility.PRIVATE
        self.project.save()

        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='project',
            target_id=self.project.pk,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(self.project.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'project')
        self.assertIsNone(data['title'])
        self.assertIsNone(data['slug'])
        self.assertIsNone(data['thumbnail_url'])
        self.assertIsNone(data['short_description'])
        self.assertEqual(data['tags'], [])
        self.assertFalse(data['is_available'])
        self.assertEqual(
            data['unavailable_reason'],
            'This item is currently unavailable.',
        )

    def test_project_unlisted_card_fields(self):
        self.project.visibility = ProjectVisibility.UNLISTED
        self.project.save()

        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='project',
            target_id=self.project.pk,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(self.project.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'project')
        self.assertIsNone(data['title'])
        self.assertIsNone(data['slug'])
        self.assertIsNone(data['thumbnail_url'])
        self.assertIsNone(data['short_description'])
        self.assertEqual(data['tags'], [])
        self.assertFalse(data['is_available'])
        self.assertEqual(
            data['unavailable_reason'],
            'This item is currently unavailable.',
        )

    def test_project_deleted_card_fields(self):
        project_id = self.project.pk
        self.project.delete()

        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='project',
            target_id=project_id,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(project_id))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'project')
        self.assertIsNone(data['title'])
        self.assertIsNone(data['slug'])
        self.assertIsNone(data['thumbnail_url'])
        self.assertIsNone(data['short_description'])
        self.assertEqual(data['tags'], [])
        self.assertFalse(data['is_available'])
        self.assertEqual(
            data['unavailable_reason'],
            'This item is no longer available.',
        )

    def test_startup_deleted_card_fields(self):
        startup_id = self.startup.pk
        self.startup.delete()

        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='startup',
            target_id=startup_id,
        )

        data = self.serialize(saved)

        self.assertEqual(data['id'], str(startup_id))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'startup')
        self.assertIsNone(data['title'])
        self.assertIsNone(data['slug'])
        self.assertIsNone(data['thumbnail_url'])
        self.assertIsNone(data['short_description'])
        self.assertEqual(data['tags'], [])
        self.assertFalse(data['is_available'])
        self.assertEqual(
            data['unavailable_reason'],
            'This item is no longer available.',
        )

    def test_unlisted_project_visible_to_owner(self):
        self.project.visibility = ProjectVisibility.UNLISTED
        self.project.save()

        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='project',
            target_id=self.project.pk,
        )

        data = self.serialize(saved, user=self.startup_user)

        self.assertEqual(data['id'], str(self.project.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'project')
        self.assertEqual(data['title'], self.project.title)
        self.assertEqual(data['slug'], self.project.slug)
        self.assertIsNone(data['thumbnail_url'])
        self.assertEqual(data['short_description'], self.project.short_description)
        self.assertEqual(data['tags'], [])
        self.assertTrue(data['is_available'])
        self.assertIsNone(data['unavailable_reason'])

    def test_unlisted_project_visible_to_admin(self):
        self.project.visibility = ProjectVisibility.UNLISTED
        self.project.save()

        admin_user = User.objects.create_user(
            username='admin',
            email='admin@t.com',
            password='123',
            is_staff=True,
            is_superuser=True,
        )

        saved = SavedItem.objects.create(
            investor=self.investor,
            target_type='project',
            target_id=self.project.pk,
        )

        data = self.serialize(saved, user=admin_user)

        self.assertEqual(data['id'], str(self.project.pk))
        self.assertEqual(data['saved_id'], saved.id)
        self.assertEqual(data['type'], 'project')
        self.assertEqual(data['title'], self.project.title)
        self.assertEqual(data['slug'], self.project.slug)
        self.assertIsNone(data['thumbnail_url'])
        self.assertEqual(data['short_description'], self.project.short_description)
        self.assertEqual(data['tags'], [])
        self.assertTrue(data['is_available'])
        self.assertIsNone(data['unavailable_reason'])
