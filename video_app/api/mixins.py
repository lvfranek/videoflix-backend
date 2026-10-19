from django.http import Http404
from django.shortcuts import get_object_or_404

from video_app.models import Video
from video_app.utils import HLS_RESOLUTIONS, get_hls_directory


class HlsFileMixin:
    """
    Locate HLS files of ready videos; everything else results in a 404.
    """

    def get_hls_file(self, movie_id, resolution, file_name):
        """
        Return the path of an HLS file of a ready video or raise
        Http404.
        """
        if resolution not in HLS_RESOLUTIONS:
            raise Http404('Unknown resolution.')
        get_object_or_404(Video, pk=movie_id, status=Video.Status.READY)
        file_path = get_hls_directory(movie_id, resolution) / file_name
        if not file_path.is_file():
            raise Http404('File not found.')
        return file_path
