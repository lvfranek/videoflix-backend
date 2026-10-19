from django.urls import path

from .views import HlsPlaylistView, HlsSegmentView, VideoListView

urlpatterns = [
    path('video/', VideoListView.as_view(), name='video-list'),
    path(
        'video/<int:movie_id>/<str:resolution>/index.m3u8',
        HlsPlaylistView.as_view(),
        name='video-playlist',
    ),
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>/',
        HlsSegmentView.as_view(),
        name='video-segment',
    ),
    # hls.js requests segments exactly as listed in the playlist, i.e.
    # without a trailing slash.
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>',
        HlsSegmentView.as_view(),
        name='video-segment-without-slash',
    ),
]
