from django.utils.html import linebreaks
from rest_framework import serializers
from users.models import ProfileAudit

from startups.models import Region, StartupProfile


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name']


class StartupPublicProfileSerializer(serializers.ModelSerializer):
    about_html = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField(read_only=True)
    projects_count = serializers.SerializerMethodField(read_only=True)

    regions = RegionSerializer(many=True, read_only=True)

    class Meta:
        model = StartupProfile
        fields = [
            'id',
            'company_name',
            'slug',
            'hero_image_url',
            'logo_url',
            'short_description',
            'about_html',
            'contact',
            'website',
            'tags',
            'followers_count',
            'projects_count',
            'created_at',
            'regions',
        ]

    def get_about_html(self, obj):
        if not obj.description:
            return ''
        return linebreaks(obj.description, autoescape=True)

    def get_contact(self, obj):
        return {
            'email': obj.contact_email,
            'phone': obj.contact_phone,
        }

    def get_followers_count(self, obj):
        return obj.followers_count

    def get_projects_count(self, obj):
        return obj.projects_count


class StartupProfileUpdateSerializer(serializers.ModelSerializer):
    regions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Region.objects.all(), required=False
    )

    class Meta:
        model = StartupProfile
        fields = [
            'company_name',
            'hero_image_url',
            'logo_url',
            'short_description',
            'description',
            'contact_email',
            'contact_phone',
            'website',
            'tags',
            'regions',
        ]

    def validate_website(self, value):
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                'Enter a valid URL starting with http or https.'
            )
        return value


class ProfileAuditSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    profile_id = serializers.IntegerField(source='object_id', read_only=True)
    profile_type = serializers.SerializerMethodField()

    def get_user_id(self, obj):
        return obj.user_id

    def get_profile_type(self, obj):
        return obj.content_type.model

    class Meta:
        model = ProfileAudit
        fields = [
            'id',
            'profile_type',
            'profile_id',
            'user_id',
            'timestamp',
            'changes',
        ]
