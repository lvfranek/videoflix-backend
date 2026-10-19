from rest_framework.generics import ListAPIView

from video_app.models import Video

from .serializers import VideoListSerializer


class VideoListView(ListAPIView):
    """List all playable videos, newest first (the first one is shown as hero)."""

    queryset = Video.objects.filter(status=Video.Status.READY)
    serializer_class = VideoListSerializer
