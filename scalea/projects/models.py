from django.db import models


class Project(models.Model):
    startup = models.ForeignKey("startups.StartupProfile", on_delete=models.CASCADE)
    status = models.BooleanField()
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField()
    funding_goal = models.DecimalField(
        max_digits=10, decimal_places=0, null=True, blank=True
    )
    current_funding = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
