from django.utils.html import linebreaks
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
        if not obj.description:
            return ''
        return linebreaks(obj.description, autoescape=True)

    def get_contact(self, obj):
        return {
            'email': obj.contact_email,
            'phone': obj.contact_phone,
        }

    def get_followers_count(self, obj):
        return getattr(obj, 'followers_count', 0)

    def get_projects_count(self, obj):
        return getattr(obj, 'projects_count', 0)
