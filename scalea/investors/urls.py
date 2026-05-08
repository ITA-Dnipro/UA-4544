from django.urls import path

from .views import SavedItemDetailView, SavedItemView

urlpatterns = [
    path('<int:user_id>/saved/', SavedItemView.as_view(), name='saved-items'),
    path(
        '<int:user_id>/saved/<int:saved_id>/',
        SavedItemDetailView.as_view(),
        name='saved-item-detail',
    ),
]
