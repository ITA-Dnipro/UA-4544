from django.urls import path

from .views import RegisterView, PasswordResetConfirmView, PasswordResetRequestView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('password-reset/', PasswordResetRequestView.as_view()),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name="password_reset_confirm",),
]
