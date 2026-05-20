from django.shortcuts import get_object_or_404
from investors.models import InvestorProfile
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tracking, TrackingTargetType
from .serializers import TrackingCreateSerializer, TrackingResponseSerializer


class TrackingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not getattr(request.user, 'is_investor', False):
            return Response(
                {'detail': 'Only investors can track items.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = TrackingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        investor = get_object_or_404(InvestorProfile, user=request.user)
        target_type = serializer.validated_data['target_type']
        source = serializer.validated_data.get('source')
        startup = serializer.validated_data.get('startup')
        project = serializer.validated_data.get('project')

        tracking = None
        if target_type == TrackingTargetType.STARTUP:
            tracking = Tracking.objects.filter(
                investor=investor, target_type=target_type, startup=startup
            ).first()
        elif target_type == TrackingTargetType.PROJECT:
            tracking = Tracking.objects.filter(
                investor=investor, target_type=target_type, project=project
            ).first()

        if tracking:
            resp_serializer = TrackingResponseSerializer(
                tracking, context={'request': request}
            )
            return Response(resp_serializer.data, status=status.HTTP_200_OK)

        tracking = Tracking.objects.create(
            investor=investor,
            target_type=target_type,
            startup=startup,
            project=project,
            source=source,
        )
        resp_serializer = TrackingResponseSerializer(
            tracking, context={'request': request}
        )
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class TrackingDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        tracking = get_object_or_404(Tracking, pk=pk)
        if tracking.investor.user != request.user:
            return Response(
                {'detail': 'You do not have permission to delete this tracking.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        tracking.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvestorTrackingListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TrackingResponseSerializer

    def get_queryset(self):
        investor_id = self.kwargs['investor_id']
        type_param = self.request.query_params.get('type')
        investor = get_object_or_404(InvestorProfile, pk=investor_id)
        user = self.request.user
        if not (investor.user == user or user.is_superuser):
            raise PermissionDenied(
                'You do not have permission to view this tracking list.'
            )
        qs = Tracking.objects.select_related('startup', 'project').filter(
            investor=investor
        )
        if type_param in [TrackingTargetType.STARTUP, TrackingTargetType.PROJECT]:
            qs = qs.filter(target_type=type_param)
        return qs.order_by('-created_at')
