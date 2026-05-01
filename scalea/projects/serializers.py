from rest_framework import serializers

from projects.models import Project


class ProjectCardSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'title', 'status', 'thumbnail', 'short_description']

    def get_thumbnail(self, _obj):
        """Project has no image field yet; return None until one is added."""
