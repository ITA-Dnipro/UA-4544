from django.db.models import Count
from rest_framework.generics import RetrieveAPIView

from startups.models import StartupProfile
from startups.serializers import StartupPublicProfileSerializer


class StartupPublicProfileView(RetrieveAPIView):
    queryset = StartupProfile.objects.annotate(
        followers_count=Count('savedstartup', distinct=True),
        projects_count=Count('project', distinct=True),
    )
    serializer_class = StartupPublicProfileSerializer
