from rest_framework.permissions import BasePermission


class IsProfileOwnerOrAdmin(BasePermission):
    message = 'You do not have permission to perform this action on this profile.'

    def has_object_permission(self, request, _view, obj):
        return request.user == obj.user or request.user.is_superuser
