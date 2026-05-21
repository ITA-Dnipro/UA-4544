from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from projects.models import Project, ProjectStatus

from .models import Investment, InvestmentStatus


@receiver(post_save, sender=Investment, dispatch_uid='investment_confirmed_handler')
def on_investment_confirmed(sender, instance, **_kwargs):  # noqa: ARG001

    if instance.status != InvestmentStatus.CONFIRMED or not instance.amount_invested:
        return

    Project.objects.filter(pk=instance.project_id).update(
        raised_amount=F('raised_amount') + instance.amount_invested
    )

    project = Project.objects.get(pk=instance.project_id)
    if (
        project.raised_amount >= project.target_amount
        and project.status == ProjectStatus.FUNDRAISING
    ):
        Project.objects.filter(pk=project.pk).update(status=ProjectStatus.FUNDED)
