from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProfileOwnerOrAdmin(BasePermission):
    message = 'You do not have permission to perform this action on this profile.'

    def has_object_permission(self, request, _view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user == obj.user or request.user.is_superuser
