from django.urls import path

from .views import AdminUserModerationListView, VerifyOrgAdminView

urlpatterns = [
    path('', AdminUserModerationListView.as_view(), name='admin-user-moderation-list'),
    path(
        '<int:pk>/verify-org-admin/',
        VerifyOrgAdminView.as_view(),
        name='verify-org-admin',
    ),
]
