from django.urls import path
from .views import RegisterView

from users.views import PasswordResetConfirmView, PasswordResetRequestView

urlpatterns = [
    path('password-reset/', PasswordResetRequestView.as_view()),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view()),
    path('register/', RegisterView.as_view(), name='register'),
]
