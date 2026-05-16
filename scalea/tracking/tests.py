from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from projects.models import Project
from startups.models import Startup  # adjust
from tracking.models import (
    Investment,
    InvestmentStatus,
    Tracking,
    TrackingTargetType,
)

User = get_user_model()

class TrackingModelTests(TestCase):
    def setUp(self):
        self.investor = User.objects.create_user(
            username="investor1",
            email="inv@example.com",
            password="pass",
        )
        self.project = Project.objects.create(name="Test Project")
        self.startup = Startup.objects.create(name="Test Startup")
    def test_create_tracking_for_project(self):
        t = Tracking.objects.create(
            investor=self.investor,
            target_type=TrackingTargetType.PROJECT,
            project=self.project,
            source="manual",
            meta={"note": "watchlist"},
        )
        self.assertIsNotNone(t.id)
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
        with self.assertRaises(IntegrityError):
            Tracking.objects.create(
                investor=self.investor,
                target_type=TrackingTargetType.PROJECT,
                project=self.project,
            )
            
class InvestmentModelTests(TestCase):
    def setUp(self):
        self.investor = User.objects.create_user(
            username="investor2",
            email="inv2@example.com",
            password="pass",
        )
        self.project = Project.objects.create(name="Fundable Co")
    def test_create_investment(self):
        inv = Investment.objects.create(
            investor=self.investor,
            project=self.project,
            status=InvestmentStatus.COMMITTED,
            amount_committed=Decimal("10000.00"),
            amount_invested=Decimal("0.00"),
            currency="UAH",
        )
        self.assertIsNotNone(inv.id)
        self.assertEqual(self.investor.investments.count(), 1)