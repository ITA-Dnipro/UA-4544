from django.urls import path

from uploads.views import UploadCreateView, UploadDestroyByPathView

urlpatterns = [
    path('', UploadCreateView.as_view(), name='upload-create'),
    path('delete/', UploadDestroyByPathView.as_view(), name='upload-destroy-by-path'),
]
