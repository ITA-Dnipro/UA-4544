from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from startups.models import StartupProfile

from investors.models import InvestorProfile, SavedItem, SavedStartup

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
