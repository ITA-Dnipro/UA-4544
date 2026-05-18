import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TrackingTargetType(models.TextChoices):
    STARTUP = 'startup', 'Startup'
    PROJECT = 'project', 'Project'


class TrackingSource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    SUGGESTION = 'suggestion', 'Suggestion'
    IMPORT = 'import', 'Import'


class Tracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(
        'investors.InvestorProfile',
        on_delete=models.CASCADE,
        related_name='tracking',
    )

    target_type = models.CharField(
        max_length=16,
        choices=TrackingTargetType.choices,
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tracking_entries',
    )
    startup = models.ForeignKey(
        'startups.StartupProfile',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tracking_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        choices=TrackingSource.choices,
    )
    meta = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~(
                    models.Q(project__isnull=False) & models.Q(startup__isnull=False)
                ),
                name='tracking_not_both_project_and_startup',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(project__isnull=False, startup__isnull=True)
                    | models.Q(project__isnull=True, startup__isnull=False)
                ),
                name='tracking_exactly_one_target',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        target_type=TrackingTargetType.PROJECT,
                        project__isnull=False,
                        startup__isnull=True,
                    )
                    | models.Q(
                        target_type=TrackingTargetType.STARTUP,
                        startup__isnull=False,
                        project__isnull=True,
                    )
                ),
                name='tracking_target_type_matches_fk',
            ),
            models.UniqueConstraint(
                fields=['investor', 'target_type', 'project'],
                condition=models.Q(project__isnull=False),
                name='uniq_tracking_investor_project',
            ),
            models.UniqueConstraint(
                fields=['investor', 'target_type', 'startup'],
                condition=models.Q(startup__isnull=False),
                name='uniq_tracking_investor_startup',
            ),
        ]

    @property
    def target_id(self):
        if self.project is not None:
            return self.project.id
        if self.startup is not None:
            return self.startup.id
        return None

    def clean(self):
        super().clean()
        has_project = self.project_id is not None
        has_startup = self.startup_id is not None
        if has_project and has_startup:
            raise ValidationError('Set only one of project or startup, not both.')
        if not has_project and not has_startup:
            raise ValidationError('Set exactly one of project or startup.')
        if self.target_type == TrackingTargetType.PROJECT:
            if not has_project or has_startup:
                raise ValidationError(
                    {'target_type': "Must be 'project' when project is set."}
                )
        elif (self.target_type == TrackingTargetType.STARTUP) and (
            (not has_startup) or has_project
        ):
            raise ValidationError(
                {'target_type': "Must be 'startup' when startup is set."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class InvestmentStatus(models.TextChoices):
    COMMITTED = 'committed', 'Committed'
    TRANSFERRED = 'transferred', 'Transferred'
    RETURNED = 'returned', 'Returned'
    CANCELLED = 'cancelled', 'Cancelled'


class Investment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(
        'investors.InvestorProfile',
        on_delete=models.CASCADE,
        related_name='investments',
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.PROTECT,
        related_name='investments',
    )
    status = models.CharField(
        max_length=16,
        choices=InvestmentStatus.choices,
        default=InvestmentStatus.COMMITTED,
    )
    amount_committed = models.DecimalField(max_digits=18, decimal_places=2)
    amount_invested = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='UAH')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    meta = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_committed__gte=0),
                name='investment_amount_committed_non_negative',
            ),
            models.CheckConstraint(
                check=models.Q(amount_invested__gte=0),
                name='investment_amount_invested_non_negative',
            ),
            models.CheckConstraint(
                check=models.Q(amount_committed__gte=models.F('amount_invested')),
                name='investment_committed_gte_invested',
            ),
        ]
        indexes = [
            models.Index(
                fields=['investor', 'status'],
                name='investment_inv_status_idx',
            ),
            models.Index(fields=['project'], name='investment_project_idx'),
        ]


class PortfolioSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(
        'investors.InvestorProfile',
        on_delete=models.CASCADE,
        related_name='portfolio_snapshots',
    )
    computed_at = models.DateTimeField()
    projects_count = models.PositiveIntegerField()
    total_committed = models.DecimalField(max_digits=18, decimal_places=2)
    total_invested = models.DecimalField(max_digits=18, decimal_places=2)
    summary = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(
                fields=['investor', '-computed_at'],
                name='portfolio_inv_computed_idx',
            ),
        ]
        ordering = ['-computed_at']
