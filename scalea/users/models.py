from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_startup = models.BooleanField(default=False)
    is_investor = models.BooleanField(default=False)
    is_org_admin = models.BooleanField(
        default=False,
        help_text="Designates whether this user can manage the organization's projects.",
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class PasswordResetAudit(models.Model):
    ACTION_REQUESTED = 'requested'
    ACTION_CONFIRMED = 'confirmed'
    ACTION_CHOICES = [
        (ACTION_REQUESTED, 'Password Reset Requested'),
        (ACTION_CONFIRMED, 'Password Reset Confirmed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='password_reset_audits',
    )
    email = models.EmailField(help_text='Електронна пошта, введена користувачем')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default='')
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default=ACTION_REQUESTED,
        help_text='Action performed: request or confirmation',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Password Reset Audit'
        verbose_name_plural = 'Password Reset Audits'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()} for {self.email} at {self.created_at.strftime("%Y-%m-%d %H:%M")}'
