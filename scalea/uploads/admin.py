from django.contrib import admin

from uploads.models import UploadedFile

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_name', 'mime_type', 'size', 'uploaded_by', 'created_at')
    readonly_fields = ('id', 'created_at')