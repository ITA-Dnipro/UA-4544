from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from users.permissions import IsOrgAdmin

from .models import Project, ProjectAudit, ProjectModerationStatus, ProjectVisibility
from .permissions import (
    IsProjectOwnerOrOrgAdmin,
    IsStartupUser,
    ProjectVisibilityPermission,
)
from .serializers import (
    AdminProjectSerializer,
    ProjectCardSerializer,
    ProjectDetailSerializer,
    ProjectModerateSerializer,
)


def send_project_rejected_email(project: Project, reason: str):
    startup_user = project.startup.user
    html_body = render_to_string(
        'email/project_rejected.html',
        {
            'project_title': project.title,
            'reason': reason,
            'user_name': startup_user.first_name
            or startup_user.get_full_name().strip()
            or startup_user.username
            or startup_user.email.split('@')[0],
        },
    )
    msg = EmailMultiAlternatives(
        subject='Scalea — Project moderation update',
        body=(
            f'Your project "{project.title}" has been rejected by admin moderation.\n\n'
            f'Reason: {reason}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[startup_user.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectCardSerializer
        return ProjectDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [ProjectVisibilityPermission()]

        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsStartupUser()]

        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsProjectOwnerOrOrgAdmin()]

        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Project.objects.filter(deleted_at__isnull=True)

        if self.action == 'list':
            if user.is_authenticated:
                if user.is_superuser:
                    return qs

                return qs.filter(
                    models.Q(visibility=ProjectVisibility.PUBLIC)
                    | models.Q(startup__user=user)
                ).distinct()

            return qs.filter(models.Q(visibility=ProjectVisibility.PUBLIC))

        return qs

    def perform_create(self, serializer):
        serializer.save(startup=self.request.user.startupprofile)


class AdminProjectListView(ListAPIView):
    serializer_class = AdminProjectSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        queryset = Project.objects.select_related('startup__user').order_by(
            '-created_at'
        )

        status_param = self.request.query_params.get('status')
        visibility = self.request.query_params.get('visibility')
        moderation_status = self.request.query_params.get('moderation_status')
        startup_id = self.request.query_params.get('startup')
        include_deleted = self.request.query_params.get('include_deleted', 'false')
        search = self.request.query_params.get('search')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        if moderation_status:
            queryset = queryset.filter(moderation_status=moderation_status)
        if startup_id:
            queryset = queryset.filter(startup_id=startup_id)
        if include_deleted.strip().lower() != 'true':
            queryset = queryset.filter(deleted_at__isnull=True)
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(startup__company_name__icontains=search)
            )

        return queryset


class AdminProjectModerationViewSet(viewsets.GenericViewSet):
    queryset = Project.objects.select_related('startup__user').all()
    permission_classes = [IsOrgAdmin]

    @action(detail=True, methods=['patch'], url_path='moderate')
    def moderate(self, request, pk=None):
        project = self.get_queryset().get(pk=pk)
        self.check_object_permissions(request, project)
        serializer = ProjectModerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        visibility = serializer.validated_data.get('visibility')

        changes = {'action': action_name}

        if action_name == 'approve':
            project.moderation_status = ProjectModerationStatus.APPROVED
            project.moderation_reason = ''
            changes['moderation_status'] = ProjectModerationStatus.APPROVED
        elif action_name == 'reject':
            project.moderation_status = ProjectModerationStatus.REJECTED
            project.moderation_reason = reason
            changes['moderation_status'] = ProjectModerationStatus.REJECTED
            changes['reason'] = reason
            send_project_rejected_email(project, reason)
        elif action_name == 'flag':
            project.moderation_status = ProjectModerationStatus.FLAGGED
            project.moderation_reason = ''
            changes['moderation_status'] = ProjectModerationStatus.FLAGGED
        elif action_name == 'delete':
            project.deleted_at = timezone.now()
            changes['deleted_at'] = project.deleted_at.isoformat()
        elif action_name == 'restore':
            project.deleted_at = None
            changes['deleted_at'] = None
        elif action_name == 'set_visibility':
            project.visibility = visibility
            changes['visibility'] = visibility

        project.last_moderated_at = timezone.now()
        project.save(
            update_fields=[
                'moderation_status',
                'moderation_reason',
                'deleted_at',
                'visibility',
                'last_moderated_at',
                'updated_at',
            ]
        )

        ProjectAudit.objects.create(project=project, user=request.user, changes=changes)
        return Response(AdminProjectSerializer(project).data)
