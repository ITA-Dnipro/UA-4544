from django.urls import path

from .views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationEmailView,
    VerifyEmailView,
)

urlpatterns = [
    path('password-reset/', PasswordResetRequestView.as_view()),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view()),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path(
        'resend-verification/',
        ResendVerificationEmailView.as_view(),
        name='resend-verification',
    ),
]
