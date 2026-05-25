from django.urls import path

from uploads.views import UploadCreateView, UploadDestroyView

urlpatterns = [
    path('', UploadCreateView.as_view(), name='upload-create'),
    path('<uuid:pk>/', UploadDestroyView.as_view(), name='upload-destroy'),
]