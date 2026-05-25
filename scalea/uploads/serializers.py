from rest_framework import serializers

from uploads.models import UploadedFile


class UploadedFileResponseSerializer(serializers.ModelSerializer):
    path = serializers.CharField(source='file.name', read_only=True)

    class Meta:
        model = UploadedFile
        fields = ['path', 'mime_type', 'size']
