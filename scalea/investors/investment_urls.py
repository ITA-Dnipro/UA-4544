from django.urls import path

from .views import InvestmentCreateView, InvestmentUpdateView

urlpatterns = [
    path('', InvestmentCreateView.as_view(), name='investment-create'),
    path('<int:pk>/', InvestmentUpdateView.as_view(), name='investment-update'),
]
