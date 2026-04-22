from django.conf import settings
from django.db import models


class Message(models.Model):
    """Stores a message sent from one user to another in a specific role context."""

    class Role(models.TextChoices):
        """Available user roles for sending and receiving messages."""

        STARTUP = "startup", "Startup"
        INVESTOR = "investor", "Investor"

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    sender_role = models.CharField(max_length=20, choices=Role.choices)
    receiver_role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a readable representation of the message sender and receiver."""
        return f"{self.sender} -> {self.receiver}"


class Notification(models.Model):
    """Stores a role-specific notification for a user."""

    class Role(models.TextChoices):
        """Available user roles for displaying notifications."""

        STARTUP = "startup", "Startup"
        INVESTOR = "investor", "Investor"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a readable representation of the notification recipient."""
        return f"Notification for {self.user}"
