from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from uploads.models import UploadedFile
from uploads.permissions import IsUploadOwnerOrAdmin
from uploads.serializers import UploadedFileResponseSerializer
from uploads.validators import validate_upload_file

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied


class UploadCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response(
                {'file': ['No file provided. Use form field name "file".']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            mime_type = validate_upload_file(upload)
        except DjangoValidationError as exc:
            return Response({'file': exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        instance = UploadedFile.objects.create(
            file=upload,
            original_name=upload.name,
            mime_type=mime_type,
            size=upload.size,
            uploaded_by=request.user,
        )
        serializer = UploadedFileResponseSerializer(
            instance, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UploadDestroyByPathView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        path = request.query_params.get('path', '').strip()
        if not path:
            return Response(
                {'path': ['Query parameter "path" is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent path traversal
        if '..' in path or path.startswith('/'):
            return Response(
                {'path': ['Invalid path.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = get_object_or_404(UploadedFile, file=path)

        permission = IsUploadOwnerOrAdmin()
        if not permission.has_object_permission(request, self, instance):
            raise PermissionDenied(detail=permission.message)

        if instance.file:
            instance.file.delete(save=False)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)