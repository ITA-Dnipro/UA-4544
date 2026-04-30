from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_startup = models.BooleanField(default=False)
    is_investor = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    """Model to track single-use password reset tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token_hash = models.CharField(max_length=255, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def mark_as_used(self):
        """Mark token as used (single-use enforcement)."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

    def __str__(self):
        return f'Reset token for {self.user.email} ({"used" if self.is_used else "unused"})'


class PasswordResetAuditLog(models.Model):
    """Audit log for password reset operations."""
    ACTION_CHOICES = [
        ('request', 'Password reset requested'),
        ('confirm', 'Password reset confirmed'),
        ('failed', 'Password reset failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.action} - {self.created_at}'
