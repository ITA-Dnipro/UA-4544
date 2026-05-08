from django.urls import path

from startups.views import (
    StartupListView,
    StartupProjectListView,
    StartupPublicProfileView,
)

urlpatterns = [
    path('', StartupListView.as_view(), name='startup-list'),
    path(
        '<int:pk>/', StartupPublicProfileView.as_view(), name='startup-public-profile'
    ),
    path(
        '<int:pk>/projects/', StartupProjectListView.as_view(), name='startup-projects'
    ),
]
