from django.conf import settings
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


class Investment(models.Model):
    investor_profile = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE)
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


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
