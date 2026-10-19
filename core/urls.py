"""Root URL configuration for the Videoflix backend."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('auth_app.api.urls')),
    path('api/', include('video_app.api.urls')),
    # Only thumbnails are public; videos are streamed through the authenticated API.
    re_path(
        rf'^{settings.MEDIA_URL.lstrip("/")}thumbnails/(?P<path>.+)$',
        serve,
        {'document_root': settings.MEDIA_ROOT / 'thumbnails'},
    ),
]
