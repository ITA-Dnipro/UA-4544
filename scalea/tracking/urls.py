from django.urls import path

from .views import InvestorTrackingListView, TrackingDetailView, TrackingView

urlpatterns = [
    path('', TrackingView.as_view(), name='tracking-create'),
    path('<uuid:pk>/', TrackingDetailView.as_view(), name='tracking-detail'),
    path(
        'investors/<int:investor_id>/tracking/',
        InvestorTrackingListView.as_view(),
        name='investor-tracking-list',
    ),
]
