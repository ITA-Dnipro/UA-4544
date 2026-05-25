import magic
from django.conf import settings
from django.core.exceptions import ValidationError


def detect_mime_type(file_obj) -> str:
    file_obj.seek(0)
    head = file_obj.read(2048)
    file_obj.seek(0)
    mime = magic.from_buffer(head, mime=True)
    return mime or 'application/octet-stream'


def validate_upload_file(file_obj) -> str:
    mime_type = detect_mime_type(file_obj)

    allowed = set(settings.UPLOAD_ALLOWED_MIME_TYPES)
    if mime_type not in allowed:
        raise ValidationError(
            f'File type "{mime_type}" is not allowed. '
            f'Allowed: {", ".join(sorted(allowed))}'
        )

    max_size = settings.UPLOAD_MAX_SIZE_BYTES
    size = file_obj.size
    if size is None or size > max_size:
        raise ValidationError(f'File size exceeds maximum of {max_size} bytes.')

    return mime_type
