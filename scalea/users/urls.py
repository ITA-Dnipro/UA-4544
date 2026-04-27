from django.urls import path

from users.views.auth import PasswordResetConfirmView, PasswordResetRequestView

urlpatterns = [
    path('auth/password-reset/', PasswordResetRequestView.as_view()),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view()),
]
