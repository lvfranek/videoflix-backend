from django.core.cache import cache
from django.http import FileResponse
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from video_app.models import Video
from video_app.utils import HLS_PLAYLIST_NAME, VIDEO_LIST_CACHE_TIMEOUT, get_video_list_cache_key

from .mixins import HlsFileMixin
from .serializers import VideoListSerializer


class VideoListView(ListAPIView):
    """
    List all playable videos, newest first (the first one is shown as hero).

    The serialized list is cached in Redis after the authentication check,
    so only logged-in users ever receive it.
    """

    queryset = Video.objects.filter(status=Video.Status.READY)
    serializer_class = VideoListSerializer

    def list(self, request, *args, **kwargs):
        cache_key = get_video_list_cache_key(request.build_absolute_uri('/'))
        videos = cache.get(cache_key)
        if videos is None:
            videos = list(self.get_serializer(self.get_queryset(), many=True).data)
            cache.set(cache_key, videos, VIDEO_LIST_CACHE_TIMEOUT)
        return Response(videos)


class HlsPlaylistView(HlsFileMixin, APIView):
    """Return the HLS playlist (index.m3u8) of a video in the requested resolution."""

    def get(self, request, movie_id, resolution):
        playlist_path = self.get_hls_file(movie_id, resolution, HLS_PLAYLIST_NAME)
        return FileResponse(playlist_path.open('rb'), content_type='application/vnd.apple.mpegurl')
