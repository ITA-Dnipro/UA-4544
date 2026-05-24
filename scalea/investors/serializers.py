from decimal import Decimal

from projects.models import Project, ProjectStatus, ProjectVisibility
from projects.permissions import ProjectVisibilityPermission
from rest_framework import serializers
from startups.models import StartupProfile
from tracking.models import TrackingTargetType
from tracking.serializers import TrackingResponseSerializer

from .models import Investment, InvestmentStatus, InvestorProfile, SavedItem


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
        return Investment.objects.filter(investor=obj.user).count()

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


class InvestmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = [
            'id',
            'investor',
            'project',
            'amount_committed',
            'amount_invested',
            'currency',
            'status',
            'meta',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title', 'slug', 'status', 'currency']


class DashboardTrackedSerializer(TrackingResponseSerializer):
    latest_project = serializers.SerializerMethodField()

    class Meta(TrackingResponseSerializer.Meta):
        fields = [*TrackingResponseSerializer.Meta.fields, 'latest_project']

    def get_latest_project(self, obj):
        if not self._can_view(obj):
            return None

        if obj.target_type == TrackingTargetType.PROJECT:
            project = obj.project
        else:
            projects = getattr(obj.startup, 'dashboard_public_projects', [])
            project = projects[0] if projects else None

        if project is None:
            return None
        return DashboardProjectSerializer(project).data


class DashboardInvestmentSerializer(serializers.ModelSerializer):
    investment_id = serializers.IntegerField(source='id', read_only=True)
    project = DashboardProjectSerializer(read_only=True)

    class Meta:
        model = Investment
        fields = [
            'investment_id',
            'project',
            'amount_committed',
            'amount_invested',
            'currency',
            'status',
            'created_at',
            'updated_at',
        ]


class DashboardQuerySerializer(serializers.Serializer):
    since = serializers.DateField(required=False)


ALLOWED_CURRENCIES = ['UAH', 'USD', 'EUR', 'GBP']


class InvestmentCreateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    amount_committed = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal('0.01')
    )
    currency = serializers.CharField(max_length=3, default='UAH')
    meta = serializers.JSONField(default=dict, required=False)

    def validate_currency(self, value):
        if value.upper() not in ALLOWED_CURRENCIES:
            raise serializers.ValidationError(
                f'Currency must be one of: {ALLOWED_CURRENCIES}'
            )
        return value.upper()

    def validate_project_id(self, value):
        try:
            project = Project.objects.get(pk=value)
        except Project.DoesNotExist as err:
            raise serializers.ValidationError('Project not found.') from err

        if project.visibility == ProjectVisibility.PRIVATE:
            raise serializers.ValidationError('Cannot invest in a private project.')

        if project.status != ProjectStatus.FUNDRAISING:
            raise serializers.ValidationError('Project is not currently fundraising.')

        return project

    def validate(self, attrs):
        project = attrs.get('project_id')
        currency = attrs.get('currency', 'UAH')

        if project and project.currency != currency:
            raise serializers.ValidationError(
                {
                    'currency': f'Currency must match project currency: {project.currency}'
                }
            )

        return attrs

    def validate_meta(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('meta must be a JSON object.')
        return value


class InvestmentUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[
            InvestmentStatus.CONFIRMED,
            InvestmentStatus.CANCELLED,
        ],
        required=False,
    )

    class Meta:
        model = Investment
        fields = ['amount_invested', 'status', 'meta']

    def validate_amount_invested(self, value):
        if value is not None and value < Decimal('0.01'):
            raise serializers.ValidationError('Amount invested must be positive.')
        return value

    def validate(self, attrs):

        current_status = self.instance.status if self.instance else None
        new_status = attrs.get('status', current_status)
        new_amount = attrs.get(
            'amount_invested', self.instance.amount_invested if self.instance else None
        )
        if self.instance and self.instance.status in (
            InvestmentStatus.CONFIRMED,
            InvestmentStatus.CANCELLED,
        ):
            raise serializers.ValidationError('Cannot modify a finalized investment.')

        if new_amount and new_amount > self.instance.amount_committed:
            raise serializers.ValidationError(
                {'amount_invested': 'Cannot invest more than committed amount.'}
            )

        if new_status == InvestmentStatus.CONFIRMED and (
            new_amount is None or new_amount == 0
        ):
            raise serializers.ValidationError(
                {'status': 'Cannot confirm investment without amount_invested.'}
            )

        if new_status == InvestmentStatus.CANCELLED and new_amount is not None:
            raise serializers.ValidationError(
                {'status': 'Cannot cancel investment that has amount_invested set.'}
            )
        return attrs

    def validate_meta(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('meta must be a JSON object.')
        return value
