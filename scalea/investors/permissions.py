from rest_framework.permissions import BasePermission


class IsInvestmentOwnerOrAdmin(BasePermission):
    message = 'You do not have permission to modify this investment.'

    def has_object_permission(self, request, _view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True
        return obj.investor_profile.user == request.user
