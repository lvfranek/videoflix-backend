from django.core.cache import cache
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from video_app.models import Video
from video_app.utils import VIDEO_LIST_CACHE_TIMEOUT, get_video_list_cache_key

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
