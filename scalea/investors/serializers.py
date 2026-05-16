from rest_framework import serializers

from projects.models import Project
from projects.permissions import ProjectVisibilityPermission
from startups.models import StartupProfile

from .models import InvestorProfile, SavedItem


class InvestorPublicProfileSerializer(serializers.ModelSerializer):
    investments_count = serializers.SerializerMethodField()
    saved_startups_count = serializers.SerializerMethodField()

    class Meta:
        model = InvestorProfile
        fields = [
            'id',
            'company_name',
            'bio',
            'investment_focus',
            'website',
            'investments_count',
            'saved_startups_count',
            'created_at',
        ]

    def get_investments_count(self, obj):
        return obj.investment_set.count()

    def get_saved_startups_count(self, obj):
        return obj.savedstartup_set.count()


class InvestorProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestorProfile
        fields = ['company_name', 'bio', 'investment_focus', 'website']


class SavedItemCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=['company', 'startup', 'project'])
    target_id = serializers.CharField(max_length=50)


class SavedItemResponseSerializer(serializers.ModelSerializer):
    saved_id = serializers.IntegerField(source='id')

    class Meta:
        model = SavedItem
        fields = ['saved_id', 'saved_at']


class SavedItemCardSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    saved_id = serializers.IntegerField(source='id', read_only=True)
    type = serializers.CharField(source='target_type')
    title = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    unavailable_reason = serializers.SerializerMethodField()

    class Meta:
        model = SavedItem
        fields = [
            'id',
            'saved_id',
            'type',
            'title',
            'slug',
            'thumbnail_url',
            'short_description',
            'tags',
            'saved_at',
            'is_available',
            'unavailable_reason',
        ]

    def get_id(self, obj):
        return str(obj.target_id)

    def get_target_obj(self, obj):
        if hasattr(obj, '_cached_target_obj'):
            return obj._cached_target_obj

        if obj.target_type in ('company', 'startup'):
            obj._cached_target_obj = StartupProfile.objects.filter(
                pk=obj.target_id
            ).first()

        elif obj.target_type == 'project':
            obj._cached_target_obj = (
                Project.objects.select_related('startup', 'startup__user')
                .filter(pk=obj.target_id)
                .first()
            )

        else:
            obj._cached_target_obj = None

        return obj._cached_target_obj

    def _can_view(self, obj):
        if hasattr(obj, '_cached_can_view'):
            return obj._cached_can_view

        target = self.get_target_obj(obj)

        if target is None:
            obj._cached_can_view = False
            return obj._cached_can_view

        if obj.target_type == 'project':
            request = self.context.get('request')

            obj._cached_can_view = (
                request is not None
                and ProjectVisibilityPermission().has_object_permission(
                    request,
                    None,
                    target,
                )
            )
            return obj._cached_can_view

        obj._cached_can_view = obj.target_type in ('startup', 'company')
        return obj._cached_can_view

    def get_is_available(self, obj):
        return self._can_view(obj)

    def get_unavailable_reason(self, obj):
        if self._can_view(obj):
            return None

        target = self.get_target_obj(obj)

        if target is None:
            return 'This item is no longer available.'

        return 'This item is currently unavailable.'

    def get_title(self, obj):
        if not self._can_view(obj):
            return None

        target = self.get_target_obj(obj)

        if target is None:
            return None

        if obj.target_type == 'project':
            return target.title

        return target.company_name

    def get_slug(self, obj):
        if not self._can_view(obj):
            return None

        target = self.get_target_obj(obj)

        if target is None:
            return None

        return getattr(target, 'slug', None)

    def get_thumbnail_url(self, obj):
        if not self._can_view(obj):
            return None

        target = self.get_target_obj(obj)

        if target is None:
            return None

        if obj.target_type == 'project':
            return None

        return getattr(target, 'logo_url', None)

    def get_short_description(self, obj):
        if not self._can_view(obj):
            return None

        target = self.get_target_obj(obj)

        if target is None:
            return None

        return getattr(target, 'short_description', None)

    def get_tags(self, obj):
        if not self._can_view(obj):
            return []

        target = self.get_target_obj(obj)

        if target is None:
            return []

        return getattr(target, 'tags', [])
