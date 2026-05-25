from rest_framework.permissions import BasePermission

from uploads.models import UploadedFile


class IsUploadOwnerOrAdmin(BasePermission):
  message = 'You do not have permission to access this file.'

  def has_object_permission(self, request, view, obj: UploadedFile):
    if request.user.is_staff or request.user.is_superuser:
      return True
    return obj.uploaded_by_id == request.user.id