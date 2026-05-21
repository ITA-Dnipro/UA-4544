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
            'visibility',
            'is_tracked',
        ]
        read_only_fields = ['id', 'slug', 'raised_amount']

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
