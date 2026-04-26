from rest_framework.generics import RetrieveAPIView

from startups.models import StartupProfile
from startups.serializers import StartupPublicProfileSerializer


class StartupPublicProfileView(RetrieveAPIView):
    queryset = StartupProfile.objects.all()
    serializer_class = StartupPublicProfileSerializer
