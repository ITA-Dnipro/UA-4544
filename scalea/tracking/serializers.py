import uuid

from django.db import IntegrityError, transaction
from investors.models import InvestorProfile
from projects.models import Project, ProjectVisibility
from projects.permissions import ProjectVisibilityPermission
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from startups.models import StartupProfile

from .models import (
    Interest,
    InterestStatus,
    Tracking,
    TrackingSource,
    TrackingTargetType,
)


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


class InterestSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    contact_opt_in = serializers.BooleanField(required=False, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = False
        self.reactivated = False

    def validate(self, attrs):
        request = self.context['request']
        user = request.user

        if not getattr(user, 'is_investor', False):
            raise PermissionDenied('Only investors can express interest.')

        investor = InvestorProfile.objects.filter(user=user).first()
        if investor is None:
            raise PermissionDenied('Investor profile required.')

        project = Project.objects.filter(id=attrs['project_id']).first()

        if project is None:
            raise NotFound('Project not found.')

        if project.visibility != ProjectVisibility.PUBLIC:
            raise NotFound('Project not found.')

        attrs['investor'] = investor
        attrs['project'] = project
        return attrs

    def create(self, validated_data):
        validated_data.pop('project_id', None)
        self.created = False
        self.reactivated = False

        try:
            with transaction.atomic():
                interest, created = Interest.objects.get_or_create(
                    investor=validated_data['investor'],
                    project=validated_data['project'],
                    defaults={
                        'message': validated_data.get('message', ''),
                        'contact_opt_in': validated_data.get(
                            'contact_opt_in',
                            False,
                        ),
                    },
                )

                self.created = created

                if not created:
                    self._reactivate_if_archived(interest, validated_data)

        except IntegrityError:
            interest = Interest.objects.get(
                investor=validated_data['investor'],
                project=validated_data['project'],
            )
            self._reactivate_if_archived(interest, validated_data)

        return interest

    def _reactivate_if_archived(self, interest, validated_data):
        if interest.status != InterestStatus.ARCHIVED:
            return

        interest.status = InterestStatus.EXPRESSED
        interest.message = validated_data.get('message', '')
        interest.contact_opt_in = validated_data.get(
            'contact_opt_in',
            False,
        )
        interest.save(
            update_fields=[
                'status',
                'message',
                'contact_opt_in',
                'updated_at',
            ]
        )
        self.reactivated = True


class InterestResponseSerializer(serializers.ModelSerializer):
    investor = serializers.IntegerField(source='investor.user_id', read_only=True)
    project_id = serializers.UUIDField(source='project.id', read_only=True)
    status = serializers.ChoiceField(
        choices=InterestStatus.choices,
        read_only=True,
    )

    class Meta:
        model = Interest
        fields = [
            'id',
            'project_id',
            'investor',
            'status',
        ]
