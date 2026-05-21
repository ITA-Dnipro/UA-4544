from django.urls import path

from .views import InvestorInvestmentListView, SavedItemDetailView, SavedItemView

urlpatterns = [
    path('<int:user_id>/saved/', SavedItemView.as_view(), name='saved-items'),
    path(
        '<int:user_id>/saved/<int:saved_id>/',
        SavedItemDetailView.as_view(),
        name='saved-item-detail',
    ),
    path(
        '<int:investor_id>/investments/',
        InvestorInvestmentListView.as_view(),
        name='investor-investments',
    ),
]
