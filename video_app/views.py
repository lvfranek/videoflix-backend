from pathlib import Path

from django.conf import settings
from django.views.static import serve


def serve_thumbnail(request, path):
    """
    Serve a video thumbnail; only this media folder is public, videos go
    through the API.
    """
    return serve(
        request, path, document_root=Path(settings.MEDIA_ROOT) / 'thumbnails'
    )
