from django.urls import path

from .views import HlsPlaylistView, VideoListView

urlpatterns = [
    path('video/', VideoListView.as_view(), name='video-list'),
    path(
        'video/<int:movie_id>/<str:resolution>/index.m3u8',
        HlsPlaylistView.as_view(),
        name='video-playlist',
    ),
]
