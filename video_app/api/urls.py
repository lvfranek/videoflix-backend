"""
URLs of the video API.

Segments are routed with and without a trailing slash: the endpoint
documentation uses a slash, while hls.js requests segments exactly as
they are listed in the playlist, i.e. without one.
"""

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
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>',
        HlsSegmentView.as_view(),
        name='video-segment-without-slash',
    ),
]
