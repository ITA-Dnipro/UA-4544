from django.shortcuts import get_object_or_404
from projects.models import Project
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from startups.models import StartupProfile

from .models import InvestorProfile, SavedItem
from .serializers import SavedItemCreateSerializer, SavedItemResponseSerializer


class SavedItemView(APIView):
    permission_classes = [IsAuthenticated]

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
