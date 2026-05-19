from django.urls import path

from startups.views import (
    RegionDetailView,
    RegionListCreateView,
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
    path(
        'regions/',
        RegionListCreateView.as_view(),
        name='region-list-create'
    ),
    path(
        'regions/<int:pk>/',
        RegionDetailView.as_view(),
        name='region-detail'
    ),
]
