import hashlib

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='password_reset_audits',
    )
    email = models.EmailField(help_text='Електронна пошта, введена користувачем')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    token_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'Password Reset Audit'
        verbose_name_plural = 'Password Reset Audits'
        ordering = ['-created_at']

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and timezone.now() >= self.expires_at

    @property
    def is_active(self) -> bool:
        return not self.revoked and not self.is_used and not self.is_expired

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])

    def __str__(self):
        return f'Reset requested for {self.email} at {self.created_at.strftime("%Y-%m-%d %H:%M")}'
