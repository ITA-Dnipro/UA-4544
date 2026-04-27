import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.utils.text import slugify


class ProjectStatus(models.TextChoices):
    IDEA = 'idea', 'Idea'
    MVP = 'mvp', 'MVP'
    FUNDRAISING = 'fundraising', 'Fundraising'
    FUNDED = 'funded', 'Funded'
    CLOSED = 'closed', 'Closed'


class ProjectVisibility(models.TextChoices):
    PUBLIC = 'public', 'Public'
    PRIVATE = 'private', 'Private'
    UNLISTED = 'unlisted', 'Unlisted'


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    startup = models.ForeignKey(
        'startups.StartupProfile',
        on_delete=models.CASCADE,
        related_name='projects',
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
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0'))]
    )
    raised_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    currency = models.CharField(max_length=3, default='UAH')

    visibility = models.CharField(
        max_length=16,
        choices=ProjectVisibility.choices,
        default=ProjectVisibility.PUBLIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['status'], name='project_status_idx')]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            max_len = self._meta.get_field('slug').max_length
            base = (slugify(self.title) or 'project')[: max_len - 6]
            slug = base
            n = 2
            self.slug = slug
            update_fields = kwargs.get('update_fields')
            if update_fields is not None and 'slug' not in update_fields:
                kwargs['update_fields'] = list(update_fields).append('slug')
            while True:
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.slug = f'{base}-{n}'
                    n += 1
        return super().save(*args, **kwargs)


class ProjectAudit(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='audits',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_audits',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['project', '-timestamp'], name='audit_proj_ts_idx'),
        ]

    def __str__(self):
        timestamp_str = (
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            if self.timestamp
            else 'unsaved_timestamp'
        )
        return f'Audit<{self.project_id} @ {timestamp_str}>'


# TODO (olgagnatenko13): add ProjectAttachment implementation
# reason: Upload model and logic is missing at the moment

# TODO (olgagnatenko13): add tags as ManyToMany implementation
# reason: Need to agree with the team, tags exist in multiple models
