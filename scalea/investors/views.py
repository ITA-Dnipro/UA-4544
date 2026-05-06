from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from startups.permissions import IsProfileOwnerOrAdmin

from investors.models import InvestorProfile
from investors.serializers import (
    InvestorProfileUpdateSerializer,
    InvestorPublicProfileSerializer,
)


class InvestorProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = InvestorProfile.objects.all()
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsProfileOwnerOrAdmin()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return InvestorProfileUpdateSerializer
        return InvestorPublicProfileSerializer
