from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class InvestorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    investment_focus = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


class InvestmentStatus(models.TextChoices):
    COMMITTED = 'committed', 'Committed'
    CONFIRMED = 'confirmed', 'Confirmed'
    CANCELLED = 'cancelled', 'Cancelled'


class Investment(models.Model):
    investor_profile = models.ForeignKey(
        InvestorProfile, on_delete=models.CASCADE, related_name='investments'
    )
    project = models.ForeignKey(
        'projects.Project', on_delete=models.PROTECT, related_name='investments'
    )
    amount_committed = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))]
    )
    amount_invested = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='UAH')
    status = models.CharField(
        max_length=32,
        choices=InvestmentStatus.choices,
        default=InvestmentStatus.COMMITTED,
    )
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.investor_profile} → {self.project} ({self.amount_committed} {self.currency})'


class SavedStartup(models.Model):
    investor_profile = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE)
    startup_profile = models.ForeignKey(
        'startups.StartupProfile', on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['investor_profile', 'startup_profile'],
                name='unique_saved_startup',
            )
        ]


class SavedItem(models.Model):
    TARGET_TYPES = [
        ('company', 'Company'),
        ('startup', 'Startup'),
        ('project', 'Project'),
    ]
    investor = models.ForeignKey(
        InvestorProfile, on_delete=models.CASCADE, related_name='saved_items'
    )
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)
    target_id = models.CharField(
        max_length=50
    )  # Note CharField because Project.id = UUID
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['investor', 'target_type', 'target_id'],
                name='unique_saved_item',
            )
        ]

    def __str__(self):
        return f'{self.investor} saved {self.target_type}:{self.target_id}'
