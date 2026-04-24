import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify


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
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=ProjectStatus.choices,
        default=ProjectStatus.IDEA,
    )
    target_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))]
    )
    raised_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))]
    )
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
    
    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            base = slugify(self.title) or "project"  # slugify("") -> ""
            slug = base
            n = 2
            while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


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
    changes = models.JSONField(default=dict)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["project", "-timestamp"], name="audit_proj_ts_idx"),
        ]

    def __str__(self):
        return f"Audit<{self.project_id} @ {self.timestamp:%Y-%m-%d %H:%M:%S}>"    


# TODO (olgagnatenko13): add ProjectAttachment implementation
# reason: Upload model and logic is missing at the moment
