from investors.models import InvestorProfile
from rest_framework import serializers
from tracking.models import Tracking, TrackingTargetType

from projects.models import PROJECT_ACTIVE_STATUSES, Project


class ProjectCardSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'title', 'status', 'thumbnail', 'short_description']

    def get_status(self, obj):
        return 'active' if obj.status in PROJECT_ACTIVE_STATUSES else 'inactive'

    def get_thumbnail(self, _obj):
        """Project has no image field yet; return None until one is added."""


class ProjectDetailSerializer(serializers.ModelSerializer):
    startup = serializers.PrimaryKeyRelatedField(read_only=True)
    is_tracked = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'startup',
            'title',
            'slug',
            'short_description',
            'description',
            'status',
            'target_amount',
            'raised_amount',
            'currency',
            'tags',
            'visibility',
            'is_tracked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'startup',
            'slug',
            'raised_amount',
            'created_at',
            'updated_at',
        ]

    def get_is_tracked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        user = request.user
        if not user.is_investor:
            return False
        try:
            investor = user.investorprofile
        except (AttributeError, InvestorProfile.DoesNotExist):
            return False
        return Tracking.objects.filter(
            investor=investor, target_type=TrackingTargetType.PROJECT, project=obj
        ).exists()


class AdminProjectSerializer(serializers.ModelSerializer):
    startup_email = serializers.EmailField(source='startup.user.email', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'status',
            'visibility',
            'moderation_status',
            'moderation_reason',
            'deleted_at',
            'startup',
            'startup_email',
            'created_at',
            'updated_at',
            'last_moderated_at',
        ]


class ProjectModerateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'flag', 'delete', 'restore', 'set_visibility']
    )
    reason = serializers.CharField(required=False, allow_blank=False)
    visibility = serializers.ChoiceField(
        choices=[choice[0] for choice in Project._meta.get_field('visibility').choices],
        required=False,
    )

    def validate(self, attrs):
        action = attrs['action']
        reason = attrs.get('reason')
        visibility = attrs.get('visibility')

        if action == 'reject' and not reason:
            raise serializers.ValidationError({'reason': 'This field is required.'})

        if action == 'set_visibility' and not visibility:
            raise serializers.ValidationError({'visibility': 'This field is required.'})

        if action != 'set_visibility' and visibility is not None:
            raise serializers.ValidationError(
                {'visibility': 'Visibility is only allowed for set_visibility action.'}
            )

        if action != 'reject' and reason is not None:
            raise serializers.ValidationError(
                {'reason': 'Reason is only allowed for reject action.'}
            )

        return attrs
