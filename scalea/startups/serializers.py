from django.utils.html import linebreaks
from django.conf import settings
from rest_framework import serializers

from startups.models import StartupProfile
from uploads.services import validate_owned_upload_path
from uploads.utils import media_url_for_path


class StartupPublicProfileSerializer(serializers.ModelSerializer):
    about_html = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField(read_only=True)
    projects_count = serializers.SerializerMethodField(read_only=True)
    logo_media_url = serializers.SerializerMethodField(read_only=True)
    hero_media_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StartupProfile
        fields = [
            'id',
            'company_name',
            'slug',
            'hero_image_url',
            'logo_url',
            'hero_media_url',
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
        return obj.followers_count

    def get_projects_count(self, obj):
        return obj.projects_count
    
    def _absolute_media(self, obj, attr):
        path = getattr(obj, attr) or ''
        if not path:
            return ''
        request = self.context.get('request')
        relative = f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"
        return request.build_absolute_uri(relative) if request else relative
    
    def get_logo_media_url(self, obj):
        return self._absolute_media(obj, 'logo_url')
    
    def get_hero_media_url(self, obj):
        return self._absolute_media(obj, 'hero_image_url')


class StartupProfileUpdateSerializer(serializers.ModelSerializer):
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
        ]

    def validate_logo_url(self, value):
        if not value:
            return ''
        return validate_owned_upload_path(value, self.context['request'].user)
    
    def validate_hero_image_url(self, value):
        if not value:
            return ''
        return validate_owned_upload_path(value, self.context['request'].user)

    def validate_website(self, value):
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                'Enter a valid URL starting with http or https.'
            )
        return value
