from django.utils.html import escape
from investors.models import SavedStartup
from rest_framework import serializers

from startups.models import StartupProfile


class StartupPublicProfileSerializer(serializers.ModelSerializer):
    about_html = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()

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
        ]

    def get_about_html(self, obj):
        if obj.description:
            return f'<p>{escape(obj.description)}</p>'
        return ''

    def get_contact(self, obj):
        return {
            'email': obj.contact_email,
            'phone': obj.contact_phone,
        }

    def get_followers_count(self, obj):
        return SavedStartup.objects.filter(startup_profile=obj).count()

    def get_projects_count(self, obj):
        return obj.project_set.count()
