from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from startups.models import StartupProfile

from investors.models import InvestorProfile, SavedStartup

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
