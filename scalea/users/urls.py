from django.urls import path

from .views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

urlpatterns = [
    path(
        'password-reset/',
        PasswordResetRequestView.as_view(),
        name='password_reset_request',
    ),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view()),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='auth-login'),
]
