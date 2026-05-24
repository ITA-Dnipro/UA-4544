from django.db import transaction
from django.shortcuts import get_object_or_404
from projects.models import Project
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from startups.models import StartupProfile

from .models import Investment, InvestmentStatus, InvestorProfile, SavedItem
from .permissions import IsInvestmentOwnerOrAdmin
from .serializers import (
    DashboardInvestmentSerializer,
    DashboardQuerySerializer,
    DashboardTrackedSerializer,
    InvestmentCreateSerializer,
    InvestmentSerializer,
    InvestmentUpdateSerializer,
    SavedItemCardSerializer,
    SavedItemCreateSerializer,
    SavedItemResponseSerializer,
)
from .services import InvestorDashboardService


class SavedItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.id != user_id and not request.user.is_superuser:
            return Response(
                {'detail': 'You can only view your own saved list.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        investor = get_object_or_404(InvestorProfile, user__id=user_id)
        queryset = SavedItem.objects.filter(investor=investor)

        type_param = request.query_params.get('type')
        if type_param in ['startup', 'project', 'company']:
            queryset = queryset.filter(target_type=type_param)

        paginator = PageNumberPagination()
        paginator.page_size_query_param = 'page_size'
        paginator.page_size = 12
        paginated_qs = paginator.paginate_queryset(
            queryset.order_by('-saved_at'), request
        )

        serializer = SavedItemCardSerializer(
            paginated_qs, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, user_id):
        if not request.user.is_investor:
            return Response(
                {'detail': 'Only investors can save items.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.user.id != user_id:
            return Response(
                {'detail': 'You can only manage your own saved list.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SavedItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_type = serializer.validated_data['target_type']
        target_id = serializer.validated_data['target_id']

        if target_type in ('startup', 'company'):
            get_object_or_404(StartupProfile, pk=target_id)
        elif target_type == 'project':
            get_object_or_404(Project, pk=target_id)

        investor = get_object_or_404(InvestorProfile, user=request.user)

        saved_item, created = SavedItem.objects.get_or_create(
            investor=investor,
            target_type=target_type,
            target_id=str(target_id),
        )

        response_serializer = SavedItemResponseSerializer(saved_item)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SavedItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, saved_id):
        if not request.user.is_investor:
            return Response(
                {'detail': 'Only investors can manage saved items.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.id != user_id:
            return Response(
                {'detail': 'You can only manage your own saved list.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        investor = get_object_or_404(InvestorProfile, user=request.user)
        saved_item = get_object_or_404(SavedItem, pk=saved_id, investor=investor)
        saved_item.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class InvestmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_investor:
            return Response(
                {'detail': 'Only investors can commit investments.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InvestmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        investment = Investment.objects.create(
            investor=request.user,
            project=serializer.validated_data['project_id'],
            amount_committed=serializer.validated_data['amount_committed'],
            currency=serializer.validated_data['currency'],
            meta=serializer.validated_data.get('meta', {}),
            status=InvestmentStatus.COMMITTED,
        )

        return Response(
            InvestmentSerializer(investment).data,
            status=status.HTTP_201_CREATED,
        )


class InvestorInvestmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, investor_id):
        if request.user.id != investor_id and not request.user.is_superuser:
            return Response(
                {'detail': 'You can only view your own investments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        investments = (
            Investment.objects.filter(investor__id=investor_id)
            .select_related('project')
            .order_by('-created_at')
        )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginator.page_size_query_param = 'page_size'
        paginated = paginator.paginate_queryset(investments, request)
        return paginator.get_paginated_response(
            InvestmentSerializer(paginated, many=True).data
        )


class InvestorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, investor_id):
        if (
            request.user.id != investor_id
            and not request.user.is_staff
            and not request.user.is_superuser
        ):
            return Response(
                {'detail': 'You can only view your own dashboard.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        investor = get_object_or_404(
            InvestorProfile.objects.select_related('user'), user_id=investor_id
        )
        query_serializer = DashboardQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        since = query_serializer.validated_data.get('since')

        service = InvestorDashboardService(investor)
        summary_data = service.build_summary()
        return Response(
            {
                'investor_id': investor_id,
                **summary_data,
                'allocation_by_project': service.allocation_by_project(),
                'recent_activity': service.recent_activity(since=since),
                'attention_required': service.attention_required(),
                'tracked': self._paginated_section(
                    request,
                    service.tracked_queryset(),
                    DashboardTrackedSerializer,
                    'tracked',
                ),
                'investments': self._paginated_section(
                    request,
                    service.investments_queryset(since=since),
                    DashboardInvestmentSerializer,
                    'investments',
                ),
            }
        )

    def _paginated_section(self, request, queryset, serializer_class, section):
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginator.page_query_param = f'{section}_page'
        paginator.page_size_query_param = f'{section}_page_size'
        paginator.max_page_size = 100
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializer_class(page, many=True, context={'request': request})
        return {
            'count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': serializer.data,
        }


class InvestmentUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        investment = get_object_or_404(Investment.objects.select_for_update(), pk=pk)

        permission = IsInvestmentOwnerOrAdmin()
        if not permission.has_object_permission(request, self, investment):
            return Response(
                {'detail': permission.message},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InvestmentUpdateSerializer(
            investment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        investment.refresh_from_db()
        return Response(InvestmentSerializer(investment).data)
