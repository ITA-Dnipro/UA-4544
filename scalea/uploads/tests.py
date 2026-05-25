from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from uploads.models import UploadedFile

User = get_user_model()

# Minimal valid file headers for python-magic / libmagic
JPEG_BYTES = b'\xff\xd8\xff\xe0' + b'0' * 200
PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'0' * 200
TEXT_BYTES = b'plain text content'


@override_settings(
    UPLOAD_MAX_SIZE_BYTES=5 * 1024 * 1024,
    UPLOAD_ALLOWED_MIME_TYPES=[
        'image/jpeg',
        'image/png',
        'image/svg+xml',
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ],
    MEDIA_ROOT='/tmp/scalea-test-media',  # isolated temp media in tests
)
class UploadAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Change to username='...' if your User model has no email field
        cls.user = User.objects.create_user(
            email='owner@test.com',
            password='test-pass-123',
        )
        cls.other_user = User.objects.create_user(
            email='other@test.com',
            password='test-pass-123',
        )

    def setUp(self):
        self.create_url = reverse('upload-create')
        self.delete_url = reverse('upload-destroy-by-path')
        self.client.force_authenticate(self.user)

    def _upload(self, file_obj, *, user=None):
        if user is not None:
            self.client.force_authenticate(user)
        return self.client.post(
            self.create_url,
            {'file': file_obj},
            format='multipart',
        )

    def test_upload_success_jpeg_returns_relative_path(self):
        file = SimpleUploadedFile('logo.jpg', JPEG_BYTES, content_type='image/jpeg')
        response = self._upload(file)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data.keys()), {'path', 'mime_type', 'size'})
        self.assertEqual(response.data['mime_type'], 'image/jpeg')
        self.assertGreater(response.data['size'], 0)

        path = response.data['path']
        self.assertFalse(path.startswith('http'))
        self.assertFalse(path.startswith('/'))
        self.assertTrue(path.startswith('uploads/'))

        upload = UploadedFile.objects.get(file=path)
        self.assertEqual(upload.uploaded_by_id, self.user.id)
        self.assertTrue(upload.file.storage.exists(path))

    def test_upload_success_png(self):
        file = SimpleUploadedFile('icon.png', PNG_BYTES, content_type='image/png')
        response = self._upload(file)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['mime_type'], 'image/png')

    def test_upload_missing_file_field(self):
        response = self.client.post(self.create_url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_upload_invalid_mime_type(self):
        file = SimpleUploadedFile('notes.txt', TEXT_BYTES, content_type='text/plain')
        response = self._upload(file)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)
        self.assertEqual(UploadedFile.objects.count(), 0)

    def test_upload_requires_authentication(self):
        self.client.force_authenticate(user=None)
        file = SimpleUploadedFile('logo.jpg', JPEG_BYTES, content_type='image/jpeg')
        response = self.client.post(
            self.create_url,
            {'file': file},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(UPLOAD_MAX_SIZE_BYTES=100)
    def test_upload_exceeds_max_size(self):
        file = SimpleUploadedFile(
            'big.jpg',
            JPEG_BYTES + (b'0' * 500),
            content_type='image/jpeg',
        )
        response = self._upload(file)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_delete_by_path_success(self):
        create_resp = self._upload(
            SimpleUploadedFile('logo.jpg', JPEG_BYTES, content_type='image/jpeg')
        )
        path = create_resp.data['path']

        delete_resp = self.client.delete(f'{self.delete_url}?path={path}')

        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UploadedFile.objects.filter(file=path).exists())

    def test_delete_forbidden_for_non_owner(self):
        create_resp = self._upload(
            SimpleUploadedFile('logo.jpg', JPEG_BYTES, content_type='image/jpeg')
        )
        path = create_resp.data['path']

        self.client.force_authenticate(self.other_user)
        delete_resp = self.client.delete(f'{self.delete_url}?path={path}')

        self.assertEqual(delete_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(UploadedFile.objects.filter(file=path).exists())

    def test_delete_missing_path_query_param(self):
        response = self.client.delete(self.delete_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('path', response.data)

    def test_delete_invalid_path_traversal(self):
        response = self.client.delete(
            f'{self.delete_url}?path=../etc/passwd'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('path', response.data)

    def test_delete_invalid_path_leading_slash(self):
        response = self.client.delete(
            f'{self.delete_url}?path=/uploads/fake/logo.jpg'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_not_found(self):
        response = self.client.delete(
            f'{self.delete_url}?path=uploads/00000000-0000-0000-0000-000000000000/missing.jpg'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_requires_authentication(self):
        create_resp = self._upload(
            SimpleUploadedFile('logo.jpg', JPEG_BYTES, content_type='image/jpeg')
        )
        path = create_resp.data['path']

        self.client.force_authenticate(user=None)
        delete_resp = self.client.delete(f'{self.delete_url}?path={path}')

        self.assertEqual(delete_resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(UploadedFile.objects.filter(file=path).exists())