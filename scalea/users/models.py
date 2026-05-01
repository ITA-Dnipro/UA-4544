from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import models
from django.conf import settings

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


class PasswordResetAudit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='password_reset_audits'
    )
    email = models.EmailField(help_text="Електронна пошта, введена користувачем")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Password Reset Audit"
        verbose_name_plural = "Password Reset Audits"
        ordering = ['-created_at']

    def __str__(self):
        return f"Reset requested for {self.email} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"