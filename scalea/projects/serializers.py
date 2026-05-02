from rest_framework import serializers

from projects.models import Project


class ProjectCardSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'title', 'status', 'thumbnail', 'short_description']

    def get_status(self, obj):
        return 'active' if obj.status in ['idea', 'mvp', 'fundraising'] else 'inactive'

    def get_thumbnail(self, _obj):
        """Project has no image field yet; return None until one is added."""
