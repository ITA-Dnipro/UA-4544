from django.urls import path

from startups.views import StartupPublicProfileView

urlpatterns = [
    path('<int:pk>/', StartupPublicProfileView.as_view(), name='startup-public-profile'),
]
