from rest_framework import permissions

from .models import ProjectVisibility


class IsStartupUser(permissions.BasePermission):
    message = 'Only users with a Startup profile can create projects.'

    def has_permission(self, request, _view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_startup', False)
        )


class IsProjectOwnerOrAdmin(permissions.BasePermission):
    message = 'You do not have permission to perform this action on this project.'

    def has_object_permission(self, request, _view, obj):
        return request.user == obj.startup.user or request.user.is_superuser


class ProjectVisibilityPermission(permissions.BasePermission):
    def has_object_permission(self, request, _view, obj):
        if obj.visibility == ProjectVisibility.PUBLIC:
            return True

        if obj.visibility == ProjectVisibility.UNLISTED:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        return obj.startup.user == request.user or request.user.is_superuser
