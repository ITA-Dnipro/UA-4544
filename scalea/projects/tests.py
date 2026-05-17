from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from investors.models import Investment, InvestorProfile
from projects.models import Project, ProjectStatus, ProjectVisibility
from startups.models import StartupProfile
from users.models import User


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


class ProjectAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', is_startup=True, is_org_admin=True, email='owner@test.com'
        )
        self.profile = StartupProfile.objects.create(
            user=self.owner, company_name='Owner Startup'
        )

        self.project = Project.objects.create(
            startup=self.profile, title='Initial Project', target_amount=1000
        )
        self.investor = User.objects.create_user(
            username='investor',
            is_startup=False,
            is_investor=True,
            is_org_admin=False,
            email='inv@test.com',
        )

        self.investor_profile = InvestorProfile.objects.create(
            user=self.investor, company_name='Angel Investors Inc'
        )

        self.list_url = reverse('project-list')
        self.detail_url = reverse('project-detail', kwargs={'pk': self.project.id})

    def test_create_project_restricted_to_startups(self):
        self.client.force_authenticate(user=self.investor)

        response = self.client.post(
            self.list_url,
            {'title': 'Fail', 'target_amount': 100, 'description': 'desc'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_prevent_escalation_on_create(self):
        other_user = User.objects.create_user(
            username='other', is_startup=True, email='other@test.com'
        )
        other_profile = StartupProfile.objects.create(
            user=other_user, company_name='Other Corp'
        )

        self.client.force_authenticate(user=self.owner)
        payload = {
            'title': 'My Project',
            'startup': other_profile.id,
            'target_amount': 1000,
            'description': 'Description',
        }
        response = self.client.post(self.list_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        project = Project.objects.get(title='My Project')
        self.assertEqual(project.startup, self.profile)

    def test_update_restricted_to_owner(self):
        stranger = User.objects.create_user(
            username='stranger', is_startup=True, email='s@t.com'
        )
        self.client.force_authenticate(user=stranger)

        response = self.client.patch(self.detail_url, {'title': 'Hacked Title'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_private_project_visibility(self):
        private_project = Project.objects.create(
            startup=self.profile,
            title='Secret AI',
            target_amount=10000,
            visibility=ProjectVisibility.PRIVATE,
        )
        url = reverse('project-detail', kwargs={'pk': private_project.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        stranger = User.objects.create_user(
            username='stranger_viewer', is_startup=False, email='s@v.com'
        )
        self.client.force_authenticate(user=stranger)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Secret AI')

    def test_unlisted_project_access_anonymous(self):
        project = Project.objects.create(
            title='Unlisted Project',
            startup=self.profile,
            target_amount=5000,
            visibility=ProjectVisibility.UNLISTED,
        )
        url = reverse('project-detail', kwargs={'pk': project.pk})

        self.client.logout()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unlisted_project_access_for_investor(self):
        project = Project.objects.create(
            title='Unlisted Project',
            startup=self.profile,
            target_amount=5000,
            visibility=ProjectVisibility.UNLISTED,
        )
        url = reverse('project-detail', kwargs={'pk': project.pk})

        self.client.force_authenticate(user=self.investor)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        Investment.objects.create(
            investor_profile=self.investor_profile, project=project, amount=1000
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_restricted_for_non_admin_member(self):
        member_user = User.objects.create_user(
            username='member',
            email='member@test.com',
            is_startup=True,
            is_org_admin=False,
        )
        self.client.force_authenticate(user=member_user)

        response = self.client.patch(self.detail_url, {'title': 'Hacked'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
