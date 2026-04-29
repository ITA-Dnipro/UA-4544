from django.urls import path

from startups.views import StartupProjectListView, StartupPublicProfileView

urlpatterns = [
    path('<int:pk>/', StartupPublicProfileView.as_view(), name='startup-public-profile'),
    path('<int:pk>/projects/', StartupProjectListView.as_view(), name='startup-projects'),
]
