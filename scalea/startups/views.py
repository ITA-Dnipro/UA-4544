from django.db.models import Count
from django.shortcuts import get_object_or_404
from projects.models import Project
from projects.serializers import ProjectCardSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination

from startups.models import StartupProfile
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
            qs = qs.filter(status__in=['idea', 'mvp', 'fundraising'])
        elif status_param == 'inactive':
            qs = qs.filter(status__in=['funded', 'closed'])

        return qs.order_by('-created_at')
