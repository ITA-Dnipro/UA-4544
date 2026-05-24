from decimal import Decimal

from django.db.models import Count, Prefetch, Q, Sum
from django.utils import timezone
from projects.models import Project, ProjectAudit, ProjectVisibility
from tracking.models import PortfolioSnapshot, Tracking, TrackingTargetType

from .models import Investment, InvestmentStatus


class InvestorDashboardService:
    def __init__(self, investor_profile):
        self.investor = investor_profile
        self._project_allocation = None

    def build_summary(self):
        project_allocation = self.allocation_by_project()
        active_investments = sum(
            position['commitments_count'] for position in project_allocation
        )
        latest_snapshot = PortfolioSnapshot.objects.filter(
            investor=self.investor
        ).first()

        if latest_snapshot is not None:
            total_committed = latest_snapshot.total_committed
            total_invested = latest_snapshot.total_invested
            source = 'snapshot'
            computed_at = latest_snapshot.computed_at
        else:
            total_committed = sum(
                (position['my_total_committed'] for position in project_allocation),
                Decimal('0.00'),
            )
            total_invested = sum(
                (position['my_total_invested'] for position in project_allocation),
                Decimal('0.00'),
            )
            source = 'realtime'
            computed_at = timezone.now()

        tracking_totals = Tracking.objects.filter(investor=self.investor).aggregate(
            tracked_count=Count('id'),
            projects_tracked=Count(
                'id',
                filter=Q(target_type=TrackingTargetType.PROJECT),
            ),
        )
        return {
            'summary': {
                'tracked_count': tracking_totals['tracked_count'],
                'projects_tracked': tracking_totals['projects_tracked'],
                'total_committed': total_committed,
                'total_invested': total_invested,
                'active_investments': active_investments,
            },
            'summary_meta': {
                'source': source,
                'computed_at': computed_at,
            },
        }

    def tracked_queryset(self):
        public_projects = Project.objects.filter(
            visibility=ProjectVisibility.PUBLIC
        ).order_by('-updated_at')
        return (
            Tracking.objects.filter(investor=self.investor)
            .select_related('project', 'project__startup__user', 'startup')
            .prefetch_related(
                Prefetch(
                    'startup__projects',
                    queryset=public_projects,
                    to_attr='dashboard_public_projects',
                )
            )
            .order_by('-created_at')
        )

    def investments_queryset(self):
        return (
            Investment.objects.filter(investor=self.investor.user)
            .select_related('project')
            .order_by('-created_at')
        )

    def allocation_by_project(self):
        if self._project_allocation is not None:
            return self._project_allocation

        positions = (
            Investment.objects.filter(investor=self.investor.user)
            .exclude(status=InvestmentStatus.CANCELLED)
            .values(
                'project_id',
                'project__title',
                'project__slug',
                'project__status',
                'project__currency',
                'project__target_amount',
                'project__raised_amount',
            )
            .annotate(
                commitments_count=Count('id'),
                my_total_committed=Sum('amount_committed'),
                my_total_invested=Sum('amount_invested'),
            )
            .order_by('-my_total_invested', '-my_total_committed', 'project__title')
        )
        self._project_allocation = [
            self._format_allocation(position) for position in positions
        ]
        return self._project_allocation

    def _format_allocation(self, position):
        zero = Decimal('0.00')
        target_amount = position['project__target_amount']
        raised_amount = position['project__raised_amount']
        my_total_invested = position['my_total_invested'] or zero
        remaining_amount = max(target_amount - raised_amount, zero)
        other_investors_invested = max(raised_amount - my_total_invested, zero)

        return {
            'project': {
                'id': str(position['project_id']),
                'title': position['project__title'],
                'slug': position['project__slug'],
                'status': position['project__status'],
                'currency': position['project__currency'],
                'target_amount': target_amount,
                'raised_amount': raised_amount,
                'remaining_amount': remaining_amount,
                'funding_progress_percent': self._percentage(
                    raised_amount, target_amount
                ),
            },
            'commitments_count': position['commitments_count'],
            'my_total_committed': position['my_total_committed'] or zero,
            'my_total_invested': my_total_invested,
            'other_investors_invested': other_investors_invested,
            'my_share_of_project_raised_percent': self._percentage(
                my_total_invested, raised_amount
            ),
        }

    def _percentage(self, amount, total):
        if not total:
            return None
        return (amount * Decimal('100') / total).quantize(Decimal('0.01'))

    def attention_required(self, limit=5):
        pending_commitments = (
            Investment.objects.filter(
                investor=self.investor.user,
                status=InvestmentStatus.COMMITTED,
            )
            .select_related('project')
            .order_by('created_at')[:limit]
        )
        return [
            {
                'type': 'commitment_pending',
                'severity': 'action_required',
                'investment_id': investment.id,
                'project_id': str(investment.project_id),
                'project_title': investment.project.title,
                'summary': (
                    'Commitment awaiting confirmation: '
                    f'{investment.amount_committed} {investment.currency}'
                ),
                'created_at': investment.created_at,
            }
            for investment in pending_commitments
        ]

    def recent_activity(self, since=None, limit=20):
        activities = (
            ProjectAudit.objects.filter(
                Q(project__investments__investor=self.investor.user)
                | Q(
                    project__tracking_entries__investor=self.investor,
                    project__visibility=ProjectVisibility.PUBLIC,
                )
                | Q(
                    project__startup__tracking_entries__investor=self.investor,
                    project__visibility=ProjectVisibility.PUBLIC,
                )
            )
            .select_related('project')
            .distinct()
            .order_by('-timestamp')
        )
        if since is not None:
            activities = activities.filter(timestamp__date__gte=since)

        return [self._format_activity(activity) for activity in activities[:limit]]

    def _format_activity(self, activity):
        changes = activity.changes or {}
        activity_type = changes.get('event', 'project_update')
        amount = changes.get('amount_invested')
        currency = changes.get('currency')

        if activity_type == 'investment_confirmed':
            summary = f'Investment confirmed: {amount} {currency}'
            severity = 'success'
        elif activity_type == 'investment_cancelled':
            summary = 'Investment commitment cancelled'
            severity = 'attention'
        elif 'status' in changes:
            status_change = changes['status']
            new_status = (
                status_change.get('to')
                if isinstance(status_change, dict)
                else status_change
            )
            summary = f'Status changed to {new_status}'
            severity = 'success' if new_status == 'funded' else 'info'
        else:
            summary = 'Project information updated'
            severity = 'info'

        return {
            'type': activity_type,
            'source': 'project_audit',
            'actor_id': activity.user_id,
            'severity': severity,
            'project_id': str(activity.project_id),
            'project_title': activity.project.title,
            'summary': summary,
            'timestamp': activity.timestamp,
        }
