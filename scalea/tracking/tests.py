from datetime import datetime, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from investors.models import InvestorProfile
from projects.models import Project
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
