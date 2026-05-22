from django.db.models import F
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from projects.models import Project, ProjectAudit, ProjectStatus

from .models import Investment, InvestmentStatus

_FINALIZED = (InvestmentStatus.CONFIRMED, InvestmentStatus.CANCELLED)


@receiver(pre_save, sender=Investment, dispatch_uid='track_investment_pre_save')
def track_previous_status(sender, instance, **_kwargs):  # noqa: ARG001

    if instance.pk:
        try:
            old = Investment.objects.get(pk=instance.pk)
            instance._prev_status = old.status
        except Investment.DoesNotExist:
            instance._prev_status = None
    else:
        instance._prev_status = None


@receiver(post_save, sender=Investment, dispatch_uid='investment_status_handler')
def on_investment_status_changed(sender, instance, **_kwargs):  # noqa: ARG001

    prev_status = getattr(instance, '_prev_status', None)

    if instance.status not in _FINALIZED:
        return

    if prev_status == instance.status:
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
