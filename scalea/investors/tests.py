from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from projects.models import Project, ProjectAudit, ProjectStatus, ProjectVisibility
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from startups.models import StartupProfile
from tracking.models import PortfolioSnapshot, Tracking, TrackingTargetType
from users.models import ProfileAudit

from investors.models import (
    Investment,
    InvestmentStatus,
    InvestorProfile,
    SavedItem,
    SavedStartup,
)
from investors.serializers import SavedItemCardSerializer

User = get_user_model()


def _profile_audits(profile):
    return ProfileAudit.objects.filter(
        content_type=ContentType.objects.get_for_model(profile),
        object_id=profile.pk,
    )


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

        audit = _profile_audits(self.profile).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, self.owner_user)
        self.assertEqual(
            audit.changes['company_name'],
            {'old': 'Alpha VC', 'new': 'Updated Alpha VC'},
        )

    def test_investor_history_endpoint_returns_audit_entries(self):
        ProfileAudit.objects.create(
            profile=self.profile,
            user=self.owner_user,
            changes={'bio': {'old': 'Old bio', 'new': 'New bio'}},
        )
        url = reverse('investor-profile-history', kwargs={'pk': self.profile.pk})

        self.client.force_authenticate(user=self.owner_user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            response.data['results'][0]['profile_type'],
            'investorprofile',
        )
        self.assertEqual(response.data['results'][0]['profile_id'], self.profile.pk)

    def test_investor_revert_restores_latest_change(self):
        self.client.force_authenticate(user=self.owner_user)
        self.client.patch(self.url, {'bio': 'Updated investor bio'}, format='json')
        url = reverse('investor-profile-revert', kwargs={'pk': self.profile.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'Early-stage tech focus.')
        self.assertEqual(_profile_audits(self.profile).count(), 2)

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

    def test_get_unauthenticated_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Alpha VC')


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


class InvestmentAPITests(APITestCase):
    def setUp(self):

        self.startup_user = User.objects.create_user(
            username='startup@test.com',
            email='startup@test.com',
            password='Password123!',
            is_startup=True,
        )
        self.startup = StartupProfile.objects.create(
            user=self.startup_user, company_name='Test Startup'
        )
        self.project = Project.objects.create(
            startup=self.startup,
            title='Test Project',
            description='desc',
            target_amount=1_000_000,
            currency='UAH',
            status='fundraising',
            visibility=ProjectVisibility.PUBLIC,
        )

        self.investor_user = User.objects.create_user(
            username='investor@test.com',
            email='investor@test.com',
            password='Password123!',
            is_investor=True,
        )
        self.investor_profile = InvestorProfile.objects.create(
            user=self.investor_user, company_name='Test VC'
        )

        self.non_investor_user = self.startup_user

        self.create_url = '/api/investments/'
        self.list_url = f'/api/investors/{self.investor_user.id}/investments/'

    def test_create_success_returns_201(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {
            'project_id': str(self.project.pk),
            'amount_committed': '10000',
            'currency': 'UAH',
        }
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'committed')

    def test_create_unauthenticated_returns_401(self):
        payload = {
            'project_id': str(self.project.pk),
            'amount_committed': '10000',
            'currency': 'UAH',
        }
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_non_investor_returns_403(self):
        self.client.force_authenticate(user=self.non_investor_user)
        payload = {
            'project_id': str(self.project.pk),
            'amount_committed': '10000',
            'currency': 'UAH',
        }
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_invalid_amount_zero_returns_400(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {
            'project_id': str(self.project.pk),
            'amount_committed': '0',
            'currency': 'UAH',
        }
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_private_project_returns_400(self):
        self.project.visibility = ProjectVisibility.PRIVATE
        self.project.save()
        self.client.force_authenticate(user=self.investor_user)
        payload = {
            'project_id': str(self.project.pk),
            'amount_committed': '10000',
            'currency': 'UAH',
        }
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_wrong_currency_returns_400(self):
        self.client.force_authenticate(user=self.investor_user)
        payload = {
            'project_id': str(self.project.pk),
            'amount_committed': '10000',
            'currency': 'JPY',
        }
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_own_investments_returns_200(self):
        self.client.force_authenticate(user=self.investor_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_other_investor_returns_403(self):
        other_user = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='Password123!',
            is_investor=True,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_by_owner_success_returns_200(self):
        investment = Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed='10000',
            currency='UAH',
        )
        self.client.force_authenticate(user=self.investor_user)
        response = self.client.patch(
            f'/api/investments/{investment.pk}/',
            {'amount_invested': '8000', 'status': 'confirmed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_by_non_owner_returns_403(self):
        investment = Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed='10000',
            currency='UAH',
        )
        self.client.force_authenticate(user=self.non_investor_user)
        response = self.client.patch(
            f'/api/investments/{investment.pk}/', {'status': 'confirmed'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_finalized_investment_returns_400(self):

        investment = Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed='10000',
            currency='UAH',
            status=InvestmentStatus.CONFIRMED,
        )
        self.client.force_authenticate(user=self.investor_user)
        response = self.client.patch(
            f'/api/investments/{investment.pk}/',
            {'amount_invested': '5000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_confirmed_updates_project_raised_amount(self):
        investment = Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed='10000',
            currency='UAH',
        )
        self.client.force_authenticate(user=self.investor_user)
        response = self.client.patch(
            f'/api/investments/{investment.pk}/',
            {'amount_invested': '8000', 'status': 'confirmed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.assertEqual(self.project.raised_amount, Decimal('8000'))

    def test_patch_confirmed_sets_project_funded_when_target_reached(self):
        self.project.target_amount = Decimal('10000')
        self.project.save()

        investment = Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed='10000',
            currency='UAH',
        )
        self.client.force_authenticate(user=self.investor_user)
        self.client.patch(
            f'/api/investments/{investment.pk}/',
            {'amount_invested': '10000', 'status': 'confirmed'},
            format='json',
        )

        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.FUNDED)


class InvestorDashboardAPITests(APITestCase):
    def setUp(self):
        self.investor_user = User.objects.create_user(
            username='dashboard-investor',
            email='dashboard-investor@example.com',
            password='Password123!',
            is_investor=True,
        )
        self.investor = InvestorProfile.objects.create(
            user=self.investor_user,
            company_name='Dashboard Capital',
        )
        self.startup_user = User.objects.create_user(
            username='dashboard-startup',
            email='dashboard-startup@example.com',
            password='Password123!',
            is_startup=True,
        )
        self.startup = StartupProfile.objects.create(
            user=self.startup_user,
            company_name='Portfolio Startup',
        )
        self.project = Project.objects.create(
            startup=self.startup,
            title='Growth Project',
            description='desc',
            target_amount=Decimal('100000.00'),
            currency='UAH',
            status=ProjectStatus.FUNDRAISING,
            visibility=ProjectVisibility.PUBLIC,
        )
        self.second_project = Project.objects.create(
            startup=self.startup,
            title='Second Project',
            description='desc',
            target_amount=Decimal('50000.00'),
            currency='UAH',
            status=ProjectStatus.MVP,
            visibility=ProjectVisibility.PUBLIC,
        )
        Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.STARTUP,
            startup=self.startup,
        )
        Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
        )
        Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed=Decimal('10000.00'),
            currency='UAH',
            status=InvestmentStatus.COMMITTED,
        )
        Investment.objects.create(
            investor=self.investor_user,
            project=self.second_project,
            amount_committed=Decimal('5000.00'),
            amount_invested=Decimal('4000.00'),
            currency='UAH',
            status=InvestmentStatus.CONFIRMED,
        )
        self.url = f'/api/investors/{self.investor_user.id}/dashboard/'

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.investor_user)

    def test_dashboard_returns_realtime_summary_and_paginated_lists(self):
        self.authenticate()

        response = self.client.get(
            self.url, {'tracked_page_size': 1, 'investments_page_size': 1}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['investor_id'], self.investor_user.id)
        self.assertEqual(response.data['summary']['tracked_count'], 2)
        self.assertEqual(response.data['summary']['projects_tracked'], 1)
        self.assertEqual(response.data['summary']['total_committed'], Decimal('15000'))
        self.assertEqual(response.data['summary']['total_invested'], Decimal('4000'))
        self.assertEqual(response.data['summary']['active_investments'], 2)
        self.assertEqual(response.data['summary_meta']['source'], 'realtime')
        self.assertEqual(response.data['tracked']['count'], 2)
        self.assertEqual(len(response.data['tracked']['results']), 1)
        self.assertEqual(response.data['investments']['count'], 2)
        self.assertEqual(len(response.data['investments']['results']), 1)
        self.assertIn('latest_project', response.data['tracked']['results'][0])
        self.assertIn('project', response.data['investments']['results'][0])
        self.assertEqual(len(response.data['attention_required']), 1)
        self.assertEqual(
            response.data['attention_required'][0]['type'], 'commitment_pending'
        )
        self.assertEqual(
            response.data['attention_required'][0]['severity'], 'action_required'
        )

    def test_dashboard_uses_latest_snapshot_for_financial_totals(self):
        PortfolioSnapshot.objects.create(
            investor=self.investor,
            computed_at=timezone.now(),
            projects_count=2,
            total_committed=Decimal('20000.00'),
            total_invested=Decimal('9000.00'),
            summary={},
        )
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_committed'], Decimal('20000'))
        self.assertEqual(response.data['summary']['total_invested'], Decimal('9000'))
        self.assertEqual(response.data['summary_meta']['source'], 'snapshot')

    def test_dashboard_aggregates_investments_and_funding_by_project(self):
        self.project.raised_amount = Decimal('12000.00')
        self.project.save(update_fields=['raised_amount'])
        Investment.objects.create(
            investor=self.investor_user,
            project=self.project,
            amount_committed=Decimal('3000.00'),
            amount_invested=Decimal('2000.00'),
            currency='UAH',
            status=InvestmentStatus.CONFIRMED,
        )
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['summary']['total_committed'], Decimal('18000.00')
        )
        self.assertEqual(response.data['summary']['total_invested'], Decimal('6000.00'))
        self.assertEqual(response.data['summary']['active_investments'], 3)
        allocation = next(
            item
            for item in response.data['allocation_by_project']
            if item['project']['id'] == str(self.project.id)
        )
        self.assertEqual(allocation['commitments_count'], 2)
        self.assertEqual(allocation['my_total_committed'], Decimal('13000.00'))
        self.assertEqual(allocation['my_total_invested'], Decimal('2000.00'))
        self.assertEqual(allocation['other_investors_invested'], Decimal('10000.00'))
        self.assertEqual(allocation['project']['target_amount'], Decimal('100000.00'))
        self.assertEqual(allocation['project']['raised_amount'], Decimal('12000.00'))
        self.assertEqual(allocation['project']['remaining_amount'], Decimal('88000.00'))
        self.assertEqual(
            allocation['project']['funding_progress_percent'], Decimal('12.00')
        )
        self.assertEqual(
            allocation['my_share_of_project_raised_percent'], Decimal('16.67')
        )

    def test_dashboard_recent_activity_accepts_since_filter(self):
        old_activity = ProjectAudit.objects.create(
            project=self.project,
            user=self.investor_user,
            changes={'event': 'investment_cancelled'},
        )
        ProjectAudit.objects.filter(pk=old_activity.pk).update(
            timestamp=timezone.now() - timedelta(days=4)
        )
        ProjectAudit.objects.create(
            project=self.project,
            user=self.investor_user,
            changes={
                'event': 'investment_confirmed',
                'amount_invested': '2500.00',
                'currency': 'UAH',
            },
        )
        self.authenticate()

        response = self.client.get(
            self.url,
            {'since': (timezone.now().date() - timedelta(days=1)).isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['recent_activity']), 1)
        self.assertEqual(
            response.data['recent_activity'][0]['type'], 'investment_confirmed'
        )
        self.assertEqual(response.data['recent_activity'][0]['source'], 'project_audit')
        self.assertEqual(
            response.data['recent_activity'][0]['actor_id'], self.investor_user.id
        )
        self.assertEqual(response.data['recent_activity'][0]['severity'], 'success')
        self.assertIn('2500.00 UAH', response.data['recent_activity'][0]['summary'])

    def test_dashboard_since_filters_investments_not_current_portfolio(self):
        Investment.objects.filter(project=self.project).update(
            created_at=timezone.now() - timedelta(days=4)
        )
        self.authenticate()

        response = self.client.get(
            self.url, {'since': timezone.now().date().isoformat()}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['investments']['count'], 1)
        self.assertEqual(
            response.data['investments']['results'][0]['project']['id'],
            str(self.second_project.id),
        )
        self.assertEqual(response.data['summary']['total_committed'], Decimal('15000'))
        self.assertEqual(len(response.data['allocation_by_project']), 2)

    def test_dashboard_activity_includes_public_project_from_tracked_startup(self):
        Investment.objects.filter(project=self.second_project).delete()
        ProjectAudit.objects.create(
            project=self.second_project,
            user=self.startup_user,
            changes={'status': {'from': 'idea', 'to': 'mvp'}},
        )
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(len(response.data['recent_activity']), 1)
        self.assertEqual(
            response.data['recent_activity'][0]['project_id'],
            str(self.second_project.id),
        )

    def test_dashboard_activity_does_not_expose_private_tracked_project(self):
        Investment.objects.all().delete()
        Tracking.objects.filter(target_type=TrackingTargetType.PROJECT).delete()
        self.second_project.visibility = ProjectVisibility.PRIVATE
        self.second_project.save(update_fields=['visibility'])
        ProjectAudit.objects.create(
            project=self.second_project,
            user=self.startup_user,
            changes={'status': {'from': 'idea', 'to': 'mvp'}},
        )
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.data['recent_activity'], [])

    def test_dashboard_rejects_other_investor(self):
        other_user = User.objects.create_user(
            username='other-dashboard-investor',
            email='other-dashboard@example.com',
            password='Password123!',
            is_investor=True,
        )
        self.authenticate(other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_allows_admin(self):
        admin = User.objects.create_superuser(
            username='dashboard-admin',
            email='dashboard-admin@example.com',
            password='Password123!',
        )
        self.authenticate(admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dashboard_rejects_invalid_since_date(self):
        self.authenticate()

        response = self.client.get(self.url, {'since': 'not-a-date'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
