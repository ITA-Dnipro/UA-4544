from django.urls import path

from .views import TrackingDetailView, TrackingView

urlpatterns = [
    path('', TrackingView.as_view(), name='tracking-create'),
    path('<uuid:pk>/', TrackingDetailView.as_view(), name='tracking-detail'),
]
