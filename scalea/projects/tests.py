
from django.test import TestCase
from startups.models import StartupProfile

from decimal import Decimal

from django.test import TestCase
from startups.models import StartupProfile
from users.models import User

from projects.models import Project, ProjectStatus, ProjectVisibility



class ProjectModelTests(TestCase):
    def test_project_creation(self):
        user = User.objects.create_user(
            username='startupuser',
            email='startup@example.com',
            password='123qwe!@#',
            is_startup=True,
            is_investor=False,
            is_verified=True,
        )

        startup_profile = StartupProfile.objects.create(
            user=user,
            company_name='Startup Company',
            description='Startup description',
            website='https://www.startupcompany.com',
        )

        project = Project.objects.create(
            startup=startup_profile,
            title='AI Matching Platform',
            slug='my-project',
            short_description='Fundraising platform',
            description='Platform connecting startups with investors',
            target_amount=500000,
        )

        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(project.startup, startup_profile)
        self.assertEqual(project.title, 'AI Matching Platform')
        self.assertEqual(project.slug, 'my-project')
        self.assertEqual(project.raised_amount, 0)
        self.assertEqual(project.currency, 'UAH')
        self.assertEqual(project.slug, 'my-project')
        self.assertEqual(project.target_amount, Decimal('500000'))
        self.assertEqual(project.status, ProjectStatus.IDEA)
        self.assertEqual(project.visibility, ProjectVisibility.PUBLIC)
