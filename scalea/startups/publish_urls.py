from django.urls import path

from startups.views import PublishProfileView

urlpatterns = [
    path('<int:pk>/publish/', PublishProfileView.as_view(), name='startup-publish'),
]
