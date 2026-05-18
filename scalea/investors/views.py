from django.shortcuts import get_object_or_404
from projects.models import Project
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from startups.models import StartupProfile

from .models import InvestorProfile, SavedItem
from .serializers import (
    SavedItemCardSerializer,
    SavedItemCreateSerializer,
    SavedItemResponseSerializer,
)


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
