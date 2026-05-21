from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from investors.models import Investment, InvestorProfile
from rest_framework import status
from rest_framework.test import APITestCase
from startups.models import StartupProfile
from users.models import User

from projects.models import (
    Project,
    ProjectAudit,
    ProjectModerationStatus,
    ProjectStatus,
    ProjectVisibility,
)


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


class AdminProjectModerationTests(APITestCase):
    def setUp(self):
        self.org_admin = User.objects.create_user(
            username='org_admin',
            email='orgadmin@test.com',
            password='StrongPassword123!',
            is_org_admin=True,
        )
        self.superadmin = User.objects.create_user(
            username='super',
            email='super@test.com',
            password='StrongPassword123!',
            is_superuser=True,
        )
        self.startup_user = User.objects.create_user(
            username='startup',
            email='startup@test.com',
            password='StrongPassword123!',
            is_startup=True,
        )
        self.startup = StartupProfile.objects.create(
            user=self.startup_user, company_name='Test Startup'
        )
        self.project = Project.objects.create(
            startup=self.startup,
            title='Moderation Target',
            description='Needs review',
            target_amount=1000,
        )

        self.list_url = '/api/admin/projects/'
        self.moderate_url = f'/api/admin/projects/{self.project.id}/moderate/'

    def test_admin_list_requires_org_admin_or_superadmin(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.startup_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.org_admin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_superadmin_can_moderate_project(self):
        self.client.force_authenticate(user=self.superadmin)

        response = self.client.patch(
            self.moderate_url, {'action': 'approve'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(
            self.project.moderation_status, ProjectModerationStatus.APPROVED
        )

    def test_admin_can_approve_and_audit_created(self):
        self.client.force_authenticate(user=self.org_admin)
        response = self.client.patch(
            self.moderate_url, {'action': 'approve'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(
            self.project.moderation_status, ProjectModerationStatus.APPROVED
        )

        audit = ProjectAudit.objects.filter(project=self.project).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes['action'], 'approve')
        self.assertEqual(audit.changes['moderation_status'], 'approved')

    def test_admin_reject_requires_reason_and_sends_email(self):
        self.client.force_authenticate(user=self.org_admin)
        bad = self.client.patch(self.moderate_url, {'action': 'reject'}, format='json')
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

        reason = 'Incomplete financial projections'
        response = self.client.patch(
            self.moderate_url,
            {'action': 'reject', 'reason': reason},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.assertEqual(
            self.project.moderation_status, ProjectModerationStatus.REJECTED
        )
        self.assertEqual(self.project.moderation_reason, reason)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reason, mail.outbox[0].body)

    def test_admin_can_change_visibility_delete_and_restore(self):
        self.client.force_authenticate(user=self.org_admin)

        visibility_response = self.client.patch(
            self.moderate_url,
            {'action': 'set_visibility', 'visibility': ProjectVisibility.PRIVATE},
            format='json',
        )
        self.assertEqual(visibility_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.patch(
            self.moderate_url,
            {'action': 'delete'},
            format='json',
        )
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.assertEqual(self.project.visibility, ProjectVisibility.PRIVATE)
        self.assertIsNotNone(self.project.deleted_at)

        restore_response = self.client.patch(
            self.moderate_url,
            {'action': 'restore'},
            format='json',
        )
        self.assertEqual(restore_response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.assertIsNone(self.project.deleted_at)
