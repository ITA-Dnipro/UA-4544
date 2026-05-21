import uuid

from projects.models import Project
from projects.permissions import ProjectVisibilityPermission
from rest_framework import serializers
from startups.models import StartupProfile

from .models import Tracking, TrackingSource, TrackingTargetType


class TrackingCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=TrackingTargetType.choices)
    target_id = serializers.CharField()
    source = serializers.ChoiceField(
        choices=TrackingSource.choices,
        required=False,
        default=TrackingSource.MANUAL,
    )

    def validate(self, attrs):
        target_type = attrs['target_type']
        target_id = attrs['target_id']
        if target_type == TrackingTargetType.STARTUP:
            try:
                startup_id = int(target_id)
            except (ValueError, TypeError) as err:
                raise serializers.ValidationError(
                    {'target_id': 'Invalid startup id.'}
                ) from err

            startup = StartupProfile.objects.filter(id=startup_id).first()

            if startup is None:
                raise serializers.ValidationError({'target_id': 'Startup not found.'})

            attrs['startup'] = startup
            attrs['project'] = None
            attrs['target_id'] = startup_id
            return attrs

        if target_type == TrackingTargetType.PROJECT:
            try:
                project_id = uuid.UUID(str(target_id))
            except (ValueError, TypeError, AttributeError) as err:
                raise serializers.ValidationError(
                    {'target_id': 'Invalid project id.'}
                ) from err

            project = Project.objects.filter(id=project_id).first()

            if project is None:
                raise serializers.ValidationError({'target_id': 'Project not found.'})

            attrs['project'] = project
            attrs['startup'] = None
            attrs['target_id'] = project_id
            return attrs
        raise serializers.ValidationError({'target_type': 'Invalid target_type.'})


class TrackingResponseSerializer(serializers.ModelSerializer):
    investor = serializers.PrimaryKeyRelatedField(read_only=True)
    target_id = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    unavailable_reason = serializers.SerializerMethodField()

    class Meta:
        model = Tracking
        fields = [
            'id',
            'investor',
            'target_type',
            'target_id',
            'title',
            'slug',
            'thumbnail_url',
            'created_at',
            'source',
            'is_available',
            'unavailable_reason',
        ]

    def _can_view(self, obj):
        if hasattr(obj, '_cached_can_view'):
            return obj._cached_can_view
        if obj.target_type == TrackingTargetType.PROJECT and obj.project:
            request = self.context.get('request')
            result = (
                request is not None
                and ProjectVisibilityPermission().has_object_permission(
                    request,
                    None,
                    obj.project,
                )
            )
            obj._cached_can_view = result
            return result
        result = (
            obj.target_type == TrackingTargetType.STARTUP and obj.startup is not None
        )
        obj._cached_can_view = result
        return result

    def get_is_available(self, obj):
        return self._can_view(obj)

    def get_unavailable_reason(self, obj):
        if self._can_view(obj):
            return None

        if obj.target_type == TrackingTargetType.PROJECT and obj.project is None:
            return 'This item is no longer available.'

        if obj.target_type == TrackingTargetType.STARTUP and obj.startup is None:
            return 'This item is no longer available.'

        return 'This item is currently unavailable.'

    def get_target_id(self, obj):
        return str(obj.target_id)

    def get_title(self, obj):
        if not self._can_view(obj):
            return None
        if obj.target_type == TrackingTargetType.STARTUP and obj.startup:
            return obj.startup.company_name
        if obj.target_type == TrackingTargetType.PROJECT and obj.project:
            return obj.project.title
        return None

    def get_slug(self, obj):
        if not self._can_view(obj):
            return None
        if obj.target_type == TrackingTargetType.STARTUP and obj.startup:
            return getattr(obj.startup, 'slug', None)
        if obj.target_type == TrackingTargetType.PROJECT and obj.project:
            return obj.project.slug
        return None

    def get_thumbnail_url(self, obj):
        if not self._can_view(obj):
            return None
        if obj.target_type == TrackingTargetType.STARTUP and obj.startup:
            return getattr(obj.startup, 'logo_url', None)
        if obj.target_type == TrackingTargetType.PROJECT and obj.project:
            return None
        return None
