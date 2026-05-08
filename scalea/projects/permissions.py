from rest_framework import permissions

from .models import ProjectVisibility


class IsStartupUser(permissions.BasePermission):
    message = 'Only users with a Startup profile can create projects.'

    def has_permission(self, request, _view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_startup
            and hasattr(request.user, 'startupprofile')
        )


class IsProjectOwnerOrOrgAdmin(permissions.BasePermission):
    message = 'You do not have permission to perform this action on this project.'

    def has_object_permission(self, request, _view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        is_owner = obj.startup.user == user
        is_admin = user.is_org_admin and obj.startup.user == user

        return is_owner or is_admin


class ProjectVisibilityPermission(permissions.BasePermission):
    def has_object_permission(self, request, _view, obj):
        if obj.visibility == ProjectVisibility.PUBLIC:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        if obj.visibility == ProjectVisibility.UNLISTED:
            return (
                obj.startup.user == request.user
                or (request.user.is_org_admin and obj.startup.user == request.user)
                or obj.investment_set.filter(
                    investor_profile__user=request.user
                ).exists()
            )

        return obj.startup.user == request.user or (
            request.user.is_org_admin and obj.startup.user == request.user
        )
