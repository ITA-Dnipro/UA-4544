from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from projects.models import Project, ProjectAudit, ProjectStatus

from .models import Investment, InvestmentStatus

_FINALIZED = (InvestmentStatus.CONFIRMED, InvestmentStatus.CANCELLED)


@receiver(post_save, sender=Investment, dispatch_uid='investment_status_handler')
def on_investment_status_changed(sender, instance, **_kwargs):  # noqa: ARG001

    if instance.status not in _FINALIZED:
        return

    ProjectAudit.objects.create(
        project_id=instance.project_id,
        user=instance.investor,
        changes={
            'event': f'investment_{instance.status}',
            'investment_id': str(instance.pk),
            'amount_invested': (
                str(instance.amount_invested) if instance.amount_invested else None
            ),
            'currency': instance.currency,
        },
    )

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
