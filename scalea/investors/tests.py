from django.test import TestCase
from startups.models import StartupProfile
from users.models import User

from investors.models import InvestorProfile, SavedStartup


class InvestorProfileModelTests(TestCase):
    def test_investor_profile_creation(self):
        user = User.objects.create_user(
            username="investoruser",
            email="investor@example.com",
            password="123qwe!@#",
            is_startup=False,
            is_investor=True,
            is_verified=True,
        )

        investor_profile = InvestorProfile.objects.create(
            user=user,
            company_name="Investor Company",
            bio="Angel investor",
            investment_focus="AI, SaaS",
            website="https://www.investorcompany.com",
        )

        self.assertEqual(investor_profile.user, user)
        self.assertEqual(investor_profile.company_name, "Investor Company")
        self.assertEqual(investor_profile.bio, "Angel investor")
        self.assertEqual(investor_profile.investment_focus, "AI, SaaS")
        self.assertEqual(investor_profile.website, "https://www.investorcompany.com")


class SavedStartupModelTests(TestCase):
    def test_saved_startup_creation(self):
        investor_user = User.objects.create_user(
            username="investoruser",
            email="investor@example.com",
            password="123qwe!@#",
            is_startup=False,
            is_investor=True,
            is_verified=True,
        )

        startup_user = User.objects.create_user(
            username="startupuser",
            email="startup@example.com",
            password="123qwe!@#",
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        investor_profile = InvestorProfile.objects.create(
            user=investor_user,
            company_name="Investor Company",
            bio="Angel investor",
            investment_focus="AI, SaaS",
            website="https://www.investorcompany.com",
        )

        startup_profile = StartupProfile.objects.create(
            user=startup_user,
            company_name="Test Company",
            description="This is a test company.",
            website="https://www.testcompany.com",
        )

        saved_startup = SavedStartup.objects.create(
            investor_profile=investor_profile,
            startup_profile=startup_profile,
        )

        self.assertEqual(saved_startup.investor_profile, investor_profile)
        self.assertEqual(saved_startup.startup_profile, startup_profile)
