from django.test import TestCase

from projects.models import Project
from startups.models import StartupProfile
from users.models import User


class ProjectModelTests(TestCase):
    def test_project_creation(self):
        user = User.objects.create_user(
            username="startupuser",
            email="startup@example.com",
            password="123qwe!@#",
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        startup_profile = StartupProfile.objects.create(
            user=user,
            company_name="Startup Company",
            description="Startup description",
            website="https://www.startupcompany.com",
        )

        project = Project.objects.create(
            startup=startup_profile,
            status=True,
            title="AI Matching Platform",
            short_description="Platform connecting startups with investors.",
            description="Detailed project description.",
            funding_goal=500000,
            current_funding=100000,
        )

        self.assertEqual(project.startup, startup_profile)
        self.assertEqual(project.title, "AI Matching Platform")
        self.assertTrue(project.status)
        self.assertEqual(project.current_funding, 100000)
