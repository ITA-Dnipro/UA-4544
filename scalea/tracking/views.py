from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from investors.models import InvestorProfile
from projects.permissions import ProjectVisibilityPermission
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Tracking, TrackingTargetType
from .serializers import (
    InterestResponseSerializer,
    InterestSerializer,
    TrackingCreateSerializer,
    TrackingResponseSerializer,
)


class TrackingPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


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
        investor = InvestorProfile.objects.filter(user=request.user).first()
        if not investor:
            return Response(
                {'detail': 'Investor profile required.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        target_type = serializer.validated_data['target_type']
        source = serializer.validated_data.get('source')
        startup = serializer.validated_data.get('startup')
        project = serializer.validated_data.get('project')

        if target_type == TrackingTargetType.PROJECT and project is not None:
            perm = ProjectVisibilityPermission()
            if not perm.has_object_permission(request, self, project):
                return Response(
                    {'detail': 'Project not found.'}, status=status.HTTP_404_NOT_FOUND
                )

        try:
            with transaction.atomic():
                if target_type == TrackingTargetType.STARTUP:
                    tracking, created = Tracking.objects.get_or_create(
                        investor=investor,
                        target_type=target_type,
                        startup=startup,
                        defaults={'source': source},
                    )
                elif target_type == TrackingTargetType.PROJECT:
                    tracking, created = Tracking.objects.get_or_create(
                        investor=investor,
                        target_type=target_type,
                        project=project,
                        defaults={'source': source},
                    )

        except IntegrityError:
            if target_type == TrackingTargetType.STARTUP:
                tracking = Tracking.objects.get(
                    investor=investor, target_type=target_type, startup=startup
                )
            elif target_type == TrackingTargetType.PROJECT:
                tracking = Tracking.objects.get(
                    investor=investor, target_type=target_type, project=project
                )

            created = False

        resp_serializer = TrackingResponseSerializer(
            tracking, context={'request': request}
        )
        return Response(
            resp_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


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
    pagination_class = TrackingPageNumberPagination

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
        if type_param:
            if type_param not in [
                TrackingTargetType.STARTUP,
                TrackingTargetType.PROJECT,
            ]:
                raise ValidationError({'type': 'Invalid type parameter.'})
            qs = qs.filter(target_type=type_param)
        return qs.order_by('-created_at')


class InterestCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'interest'

    def post(self, request):
        serializer = InterestSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        interest = serializer.save()

        response_serializer = InterestResponseSerializer(interest)

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED if serializer.created else status.HTTP_200_OK
            ),
        )
