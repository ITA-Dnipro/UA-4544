from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_startup = models.BooleanField(default=False)
    is_investor = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )

    uid = models.CharField(max_length=255, db_index=True)

    token_hash = models.CharField(max_length=255, db_index=True)

    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["uid", "token_hash"]),
            models.Index(fields=["user", "is_used"]),
        ]

    def is_expired(self):

        return timezone.now() > self.expires_at

    def mark_used(self):

        self.is_used = True

        self.used_at = timezone.now()

        self.save(update_fields=["is_used", "used_at"])


class AuditLog(models.Model):
    ACTION_PASSWORD_RESET = "password_reset"

    ACTION_CHOICES = [
        (ACTION_PASSWORD_RESET, "Password Reset"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="audit_logs"
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    user_agent = models.TextField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    details = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "action"]),
            models.Index(fields=["timestamp"]),
        ]
