from django.urls import path

from users.views import PasswordResetConfirmView, PasswordResetRequestView

from .views import RegisterView

urlpatterns = [
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view()),
    path('register/', RegisterView.as_view(), name='register'),
]
