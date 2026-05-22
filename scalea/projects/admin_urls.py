from django.urls import path

from .views import AdminProjectListView, AdminProjectModerationViewSet

urlpatterns = [
    path('', AdminProjectListView.as_view(), name='admin-project-list'),
    path(
        '<uuid:pk>/moderate/',
        AdminProjectModerationViewSet.as_view({'patch': 'moderate'}),
        name='admin-project-moderate',
    ),
]
