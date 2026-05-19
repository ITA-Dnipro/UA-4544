from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from projects.models import PROJECT_ACTIVE_STATUSES, PROJECT_INACTIVE_STATUSES, Project
from projects.serializers import ProjectCardSerializer
from rest_framework import generics, status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from startups.diff import _build_changes, _profile_snapshot
from startups.models import ProfileAudit, StartupProfile
from startups.permissions import IsProfileOwnerOrAdmin
from startups.serializers import (
    ProfileAuditSerializer,
    StartupProfileUpdateSerializer,
    StartupPublicProfileSerializer,
)


class StartupListView(generics.ListAPIView):
    serializer_class = StartupPublicProfileSerializer

    def get_queryset(self):
        queryset = StartupProfile.objects.filter(is_published=True).annotate(
            followers_count=Count('savedstartup', distinct=True),
            projects_count=Count('projects', distinct=True),
        )
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag.strip().lower()])
        return queryset


class StartupPublicProfileView(generics.RetrieveUpdateAPIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_field = 'pk'

    def get_queryset(self):
        qs = StartupProfile.objects.annotate(
            followers_count=Count('savedstartup', distinct=True),
            projects_count=Count('projects', distinct=True),
        )

        user = self.request.user

        if self.request.method in ['PUT', 'PATCH']:
            return qs

        if user.is_authenticated:
            if user.is_staff or user.is_superuser:
                return qs
            return qs.filter(Q(is_published=True) | Q(user=user))

        return qs.filter(is_published=True)

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [IsAuthenticated(), IsProfileOwnerOrAdmin()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return StartupProfileUpdateSerializer
        return StartupPublicProfileSerializer

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()

    def update(self, request, *_args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        before = _profile_snapshot(instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        after = _profile_snapshot(instance)
        changes = _build_changes(before, after)
        if changes:
            ProfileAudit.objects.create(
                profile=instance,
                user=request.user if request.user.is_authenticated else None,
                changes=changes,
            )

        return Response(StartupPublicProfileSerializer(instance).data)


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
            before = _profile_snapshot(profile)
            updated = StartupProfile.objects.filter(
                pk=profile.pk,
                is_published=False,
            ).update(
                is_published=True,
                published_at=timezone.now(),
                published_by=request.user,
            )
            if updated:
                profile.refresh_from_db()
                after = _profile_snapshot(profile)
                changes = _build_changes(before, after)
                if changes:
                    ProfileAudit.objects.create(
                        profile=profile,
                        user=request.user if request.user.is_authenticated else None,
                        changes=changes,
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


class ProfileHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProfileHistoryView(ListAPIView):
    serializer_class = ProfileAuditSerializer
    pagination_class = ProfileHistoryPagination
    permission_classes = [IsAuthenticated, IsProfileOwnerOrAdmin]

    def get_queryset(self):
        profile = get_object_or_404(StartupProfile, user_id=self.kwargs['pk'])
        self.check_object_permissions(self.request, profile)
        return ProfileAudit.objects.filter(profile=profile).order_by('-timestamp')


class RevertProfileOneStepView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        profile = get_object_or_404(StartupProfile, user_id=pk)

        if request.user != profile.user:
            return Response(
                {'detail': 'Only owner can revert profile.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        last_audit = (
            ProfileAudit.objects.filter(profile=profile).order_by('-timestamp').first()
        )
        if not last_audit:
            return Response(
                {'detail': 'No history to revert.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = _profile_snapshot(profile)

        with transaction.atomic():
            for field, delta in last_audit.changes.items():
                if field == 'published_by_id':
                    profile.published_by_id = delta.get('old')
                else:
                    setattr(profile, field, delta.get('old'))

            profile.save()
            profile.refresh_from_db()
            after = _profile_snapshot(profile)
            revert_changes = _build_changes(before, after)
            if not revert_changes:
                return Response(
                    {'detail': 'Last history step cannot be reverted.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ProfileAudit.objects.create(
                profile=profile,
                user=request.user,
                changes=revert_changes,
            )

        return Response(
            {'detail': 'Profile reverted by one step.'},
            status=status.HTTP_200_OK,
        )
