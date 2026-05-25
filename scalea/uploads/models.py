import uuid

from django.conf import settings
from django.db import models


class Visibility(models.TextChoices):
    PUBLIC = 'public', 'Public'
    PRIVATE = 'private', 'Private'


def upload_to_path(instance, filename):
    return f'uploads/{instance.id}/{filename}'


class UploadedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=upload_to_path)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_files',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.original_name} ({self.id})'
    
    @property
    def relative_path(self) -> str:
        return self.file.name  # already relative to MEDIA_ROOT