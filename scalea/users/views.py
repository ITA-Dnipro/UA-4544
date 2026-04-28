from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import RegisterSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *_args, **_kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                'email': user.email,
                'detail': 'Verification email sent. Please check your inbox.',
            },
            status=status.HTTP_201_CREATED,
        )
