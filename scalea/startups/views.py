from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from projects.models import PROJECT_ACTIVE_STATUSES, PROJECT_INACTIVE_STATUSES, Project
from projects.serializers import ProjectCardSerializer
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from startups.models import StartupProfile
from startups.permissions import IsProfileOwnerOrAdmin
from startups.serializers import StartupPublicProfileSerializer


class StartupPublicProfileView(RetrieveAPIView):
    queryset = StartupProfile.objects.annotate(
        followers_count=Count('savedstartup', distinct=True),
        projects_count=Count('projects', distinct=True),
    )
    serializer_class = StartupPublicProfileSerializer


class ProjectCardPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 100


class StartupProjectListView(ListAPIView):
    serializer_class = ProjectCardSerializer
    pagination_class = ProjectCardPagination

    def get_queryset(self):
        startup_id = self.kwargs['pk']
        startup = get_object_or_404(StartupProfile, pk=startup_id)
        qs = Project.objects.filter(startup=startup)

        status_param = self.request.query_params.get('status', '').lower()
        if status_param == 'active':
            qs = qs.filter(status__in=PROJECT_ACTIVE_STATUSES)
        elif status_param == 'inactive':
            qs = qs.filter(status__in=PROJECT_INACTIVE_STATUSES)

        return qs.order_by('-created_at')


def _get_missing_fields(profile):
    """Return list of required fields that are not filled in."""
    missing = []
    if not profile.company_name.strip():
        missing.append('company_name')
    if not profile.description.strip():
        missing.append('description')
    if not profile.contact_email.strip():
        missing.append('contact_email')
    # TODO(#55 — olgagnatenko13): validate logo_url once Upload model is ready
    #   if not profile.logo_url:
    #       missing.append('logo_url')
    return missing


class PublishProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        profile = get_object_or_404(StartupProfile, pk=pk)

        permission = IsProfileOwnerOrAdmin()
        if not permission.has_object_permission(request, self, profile):
            return Response(
                {'detail': permission.message},
                status=status.HTTP_403_FORBIDDEN,
            )

        if profile.is_published:
            return Response(
                {'detail': 'Profile is already published.'},
                status=status.HTTP_200_OK,
            )

        missing = _get_missing_fields(profile)
        if missing:
            return Response(
                {'missing_fields': missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            updated = StartupProfile.objects.filter(
                pk=profile.pk,
                is_published=False,
            ).update(
                is_published=True,
                published_at=timezone.now(),
                published_by=request.user,
            )

        if updated == 0:
            return Response(
                {'detail': 'Profile is already published.'},
                status=status.HTTP_200_OK,
            )

        return Response(
            {'detail': 'Profile published successfully.'},
            status=status.HTTP_200_OK,
        )
