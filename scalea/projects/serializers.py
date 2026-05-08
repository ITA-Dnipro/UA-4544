from rest_framework import serializers

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
        ]
        read_only_fields = ['id', 'slug', 'raised_amount']
