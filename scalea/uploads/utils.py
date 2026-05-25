from django.conf import settings

def media_url_for_path(relative_path: str) -> str:
    # Browser URL: MEDIA_URL + path relative to MEDIA_ROOT.
    if not relative_path:
        return ''
    base = settings.MEDIA_URL.rstrip('/')
    path = relative_path.lstrip('/')
    return f'{base}/{path}'


