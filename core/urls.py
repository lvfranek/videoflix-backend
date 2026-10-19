"""Root URL configuration for the Videoflix backend."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from video_app.views import serve_thumbnail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('auth_app.api.urls')),
    path('api/', include('video_app.api.urls')),
    # Only thumbnails are public; videos are streamed through the authenticated API.
    re_path(
        rf'^{settings.MEDIA_URL.lstrip("/")}thumbnails/(?P<path>.+)$',
        serve_thumbnail,
        name='thumbnail',
    ),
]
