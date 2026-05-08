from django.db import models
from rest_framework import permissions, viewsets

from .models import Project, ProjectVisibility
from .permissions import (
    IsProjectOwnerOrOrgAdmin,
    IsStartupUser,
    ProjectVisibilityPermission,
)
from .serializers import ProjectCardSerializer, ProjectDetailSerializer


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
        qs = Project.objects.all()

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
