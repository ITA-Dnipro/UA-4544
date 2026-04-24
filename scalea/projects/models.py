import uuid

from django.conf import settings
from django.db import models


class ProjectStatus(models.TextChoices):
    IDEA = "idea", "Idea"
    MVP = "mvp", "MVP"
    FUNDRAISING = "fundraising", "Fundraising"
    FUNDED = "funded", "Funded"
    CLOSED = "closed", "Closed"

class ProjectVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted"

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    startup = models.ForeignKey(
        "startups.StartupProfile",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, default=uuid.uuid4, unique=True)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=ProjectStatus.choices,
        default=ProjectStatus.IDEA,
    )
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    raised_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="UAH")

    visibility = models.CharField(
        max_length=16,
        choices=ProjectVisibility.choices,
        default=ProjectVisibility.PUBLIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="project_status_idx")
        ]

    def __str__(self):
        return self.title


class ProjectAudit(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="audits",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()


# TODO (olgagnatenko13): add ProjectAttachment implementation
# reason: Upload model and logic is missing at the moment
