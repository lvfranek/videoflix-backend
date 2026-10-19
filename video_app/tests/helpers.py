"""Shared helpers for the video app tests."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from video_app.models import Video
from video_app.utils import get_hls_directory

IN_MEMORY_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


class VideoTestCase(APITestCase):
    """Runs every test with a temporary MEDIA_ROOT and an in-memory cache instead of Redis."""

    def setUp(self):
        self.media_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        settings_override = override_settings(MEDIA_ROOT=self.media_root, CACHES=IN_MEMORY_CACHE)
        settings_override.enable()
        self.addCleanup(settings_override.disable)


def create_video(title='Test Video', status=Video.Status.READY, **fields):
    """Create a video with a small dummy upload; no background job is started."""
    with patch('video_app.tasks.django_rq.enqueue'):
        return Video.objects.create(
            title=title,
            description='A test video.',
            category=Video.Category.DRAMA,
            video_file=SimpleUploadedFile('clip.mp4', b'not really a video', content_type='video/mp4'),
            status=status,
            **fields,
        )


def create_hls_files(video, resolutions=('480p', '720p', '1080p'), segments=2):
    """Write a fake HLS playlist and segments for a video into the media folder."""
    for resolution in resolutions:
        folder = get_hls_directory(video.pk, resolution)
        folder.mkdir(parents=True)
        (folder / 'index.m3u8').write_text('#EXTM3U\n#EXT-X-ENDLIST\n')
        for number in range(segments):
            (folder / f'{number:03d}.ts').write_bytes(b'segment')
