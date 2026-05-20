from datetime import datetime, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from investors.models import InvestorProfile
from projects.models import Project
from rest_framework import status
from rest_framework.test import APITestCase
from startups.models import StartupProfile

from tracking.models import (
    Investment,
    InvestmentStatus,
    PortfolioSnapshot,
    Tracking,
    TrackingTargetType,
)

User = get_user_model()


class TrackingModelTests(TestCase):
    def setUp(self):
        investor_user = User.objects.create_user(
            username='investor1',
            email='inv@example.com',
            password='pass',
        )

        startup_user = User.objects.create_user(
            username='startup_user1',
            email='startup@example.com',
            password='pass',
        )

        investor = InvestorProfile.objects.create(
            user=investor_user, company_name='Acme Capital'
        )
        startup = StartupProfile.objects.create(
            user=startup_user, company_name='Test Startup'
        )
        project = Project.objects.create(
            title='Test Project', startup=startup, target_amount=Decimal('100000.0')
        )

        self.investor = investor
        self.startup = startup
        self.project = project

    def test_create_tracking_for_project(self):
        t = Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
            source='manual',
            meta={'note': 'watchlist'},
        )
        self.assertIsNotNone(t.id)
        self.assertEqual(t.investor, self.investor)
        self.assertIsInstance(t.investor, InvestorProfile)
        self.assertEqual(t.project, self.project)
        self.assertIsNone(t.startup)
        self.assertEqual(t.target_id, self.project.pk)

    def test_create_tracking_for_startup(self):
        t = Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.STARTUP,
            startup=self.startup,
        )
        self.assertEqual(t.startup, self.startup)
        self.assertIsNone(t.project)

    def test_reject_both_project_and_startup(self):
        t = Tracking(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
            startup=self.startup,
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_reject_neither_project_nor_startup(self):
        t = Tracking(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_reject_target_type_mismatch(self):
        t = Tracking(
            investor=self.investor,
            target_type=TrackingTargetType.STARTUP,
            project=self.project,
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_unique_per_investor_and_project(self):
        Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
        )
        with self.assertRaises(ValidationError):
            Tracking.objects.create(
                investor=self.investor,
                target_type=TrackingTargetType.PROJECT,
                project=self.project,
            )

    def test_two_investors_can_track_same_project(self):
        user2 = User.objects.create_user(
            username='investor2',
            email='inv2@example.com',
            password='pass',
        )
        investor2 = InvestorProfile.objects.create(
            user=user2, company_name='Beta Partners'
        )

        Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
        )
        t2 = Tracking.objects.create(
            investor=investor2,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
        )
        self.assertEqual(t2.project, self.project)


class InvestmentModelTests(TestCase):
    def setUp(self):
        investor_user = User.objects.create_user(
            username='investor1',
            email='inv@example.com',
            password='pass',
        )
        startup_user = User.objects.create_user(
            username='startup_user1',
            email='startup@example.com',
            password='pass',
        )

        investor = InvestorProfile.objects.create(
            user=investor_user, company_name='Acme Capital'
        )
        startup = StartupProfile.objects.create(
            user=startup_user, company_name='Test Startup'
        )
        project = Project.objects.create(
            title='Test Project', startup=startup, target_amount=Decimal('100000.0')
        )
        self.investor = investor
        self.project = project

    def test_create_investment(self):
        inv = Investment.objects.create(
            investor=self.investor,
            project=self.project,
            status=InvestmentStatus.COMMITTED,
            amount_committed=Decimal('10000.00'),
            amount_invested=Decimal('0.00'),
            currency='UAH',
            meta={'round': 'seed'},
        )
        self.assertIsNotNone(inv.id)
        self.assertEqual(inv.investor, self.investor)
        self.assertEqual(inv.status, InvestmentStatus.COMMITTED)
        self.assertEqual(self.investor.investments.count(), 1)
        self.assertEqual(self.project.investments.count(), 1)
        self.assertEqual(inv.investor.user.username, 'investor1')


class PortfolioSnapshotModelTests(TestCase):
    def setUp(self):
        investor_user = User.objects.create_user(
            username='investor1',
            email='inv@example.com',
            password='pass',
        )
        investor = InvestorProfile.objects.create(
            user=investor_user, company_name='Acme Capital'
        )
        self.investor = investor

    def test_create_portfolio_snapshot(self):
        snap = PortfolioSnapshot.objects.create(
            investor=self.investor,
            computed_at=datetime(2025, 5, 16, 12, 0, tzinfo=timezone.utc),
            projects_count=2,
            total_committed=Decimal('50000.00'),
            total_invested=Decimal('25000.00'),
            summary={'irr': None, 'currency': 'UAH'},
        )
        self.assertIsNotNone(snap.id)
        self.assertEqual(self.investor.portfolio_snapshots.count(), 1)


class TrackingAPITests(APITestCase):
    def setUp(self):
        self.investor_user = User.objects.create_user(
            username='investor1',
            email='inv@example.com',
            password='pass',
            is_investor=True,
        )
        self.investor = InvestorProfile.objects.create(
            user=self.investor_user, company_name='Acme Capital'
        )
        self.startup_user = User.objects.create_user(
            username='startup1', email='startup@example.com', password='pass'
        )
        self.startup = StartupProfile.objects.create(
            user=self.startup_user, company_name='Test Startup'
        )
        self.project = Project.objects.create(
            title='Test Project',
            startup=self.startup,
            target_amount=Decimal('100000.0'),
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass',
            is_investor=True,
        )
        self.other_investor = InvestorProfile.objects.create(
            user=self.other_user, company_name='Other Capital'
        )
        self.non_investor_user = User.objects.create_user(
            username='noninv',
            email='noninv@example.com',
            password='pass',
            is_investor=False,
        )
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='pass'
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_create_tracking_returns_201(self):
        self.authenticate(self.investor_user)
        url = '/api/tracking/'
        data = {
            'target_type': 'startup',
            'target_id': str(self.startup.pk),
            'source': 'manual',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['target_type'], 'startup')
        self.assertEqual(str(response.data['target_id']), str(self.startup.pk))
        self.assertEqual(response.data['investor'], self.investor.pk)

    def test_duplicate_create_returns_200(self):
        self.authenticate(self.investor_user)
        url = '/api/tracking/'
        data = {
            'target_type': 'startup',
            'target_id': str(self.startup.pk),
            'source': 'manual',
        }
        self.client.post(url, data, format='json')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['target_type'], 'startup')

    def test_delete_tracking_returns_204(self):
        self.authenticate(self.investor_user)
        url = '/api/tracking/'
        data = {
            'target_type': 'project',
            'target_id': str(self.project.pk),
            'source': 'manual',
        }
        resp = self.client.post(url, data, format='json')
        tracking_id = resp.data['id']
        del_url = f'/api/tracking/{tracking_id}/'
        response = self.client.delete(del_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_tracking_returns_data(self):
        self.authenticate(self.investor_user)
        self.client.post(
            '/api/tracking/',
            {
                'target_type': 'startup',
                'target_id': str(self.startup.pk),
                'source': 'manual',
            },
            format='json',
        )
        self.client.post(
            '/api/tracking/',
            {
                'target_type': 'project',
                'target_id': str(self.project.pk),
                'source': 'manual',
            },
            format='json',
        )
        url = f'/api/investors/{self.investor.pk}/tracking/?type=startup'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertEqual(len(response.data['results']), 1)
        item = response.data['results'][0]
        self.assertEqual(item['target_type'], 'startup')
        self.assertIn('title', item)
        self.assertIn('slug', item)
        self.assertIn('thumbnail_url', item)

    def test_unauthorized_returns_401(self):
        url = f'/api/investors/{self.investor.pk}/tracking/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        post_url = '/api/tracking/'
        data = {
            'target_type': 'startup',
            'target_id': str(self.startup.pk),
            'source': 'manual',
        }
        response = self.client.post(post_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_investor_returns_403(self):
        self.authenticate(self.non_investor_user)
        url = '/api/tracking/'
        data = {
            'target_type': 'startup',
            'target_id': str(self.startup.pk),
            'source': 'manual',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_delete_returns_403(self):
        self.authenticate(self.investor_user)
        url = '/api/tracking/'
        data = {
            'target_type': 'project',
            'target_id': str(self.project.pk),
            'source': 'manual',
        }
        resp = self.client.post(url, data, format='json')
        tracking_id = resp.data['id']

        self.authenticate(self.other_user)
        del_url = f'/api/tracking/{tracking_id}/'
        response = self.client.delete(del_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_list_returns_403(self):
        self.authenticate(self.other_user)
        url = f'/api/investors/{self.investor.pk}/tracking/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
