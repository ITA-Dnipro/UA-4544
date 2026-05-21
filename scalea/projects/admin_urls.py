from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminProjectListView, AdminProjectModerationViewSet

router = DefaultRouter()
router.register(r'', AdminProjectModerationViewSet, basename='admin-project')

urlpatterns = [
    path('', AdminProjectListView.as_view(), name='admin-project-list'),
    path('', include(router.urls)),
]
