from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, _view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )
