import importlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import clear_url_caches
from rest_framework import status

from core import urls as root_urls

from .helpers import VideoTestCase, create_hls_files, create_video


class MediaAccessTests(VideoTestCase):
    """Only thumbnails are public; video files must not bypass the authenticated API."""

    def setUp(self):
        super().setUp()
        self.video = create_video(thumbnail=SimpleUploadedFile('thumb.jpg', b'jpg-bytes'))
        create_hls_files(self.video)

    def assert_video_files_not_served(self):
        protected_urls = (
            self.video.video_file.url,
            f'/media/videos/{self.video.pk}/720p/index.m3u8',
            f'/media/videos/{self.video.pk}/720p/000.ts',
        )
        for url in protected_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_thumbnail_is_public(self):
        response = self.client.get(self.video.thumbnail.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(response.streaming_content), b'jpg-bytes')

    def test_video_files_are_not_served_as_media(self):
        self.assert_video_files_not_served()

    def test_video_files_stay_private_in_debug_mode(self):
        # The test runner forces DEBUG=False, so load the URLs again the way local development sees them.
        self.addCleanup(clear_url_caches)
        self.addCleanup(importlib.reload, root_urls)
        with override_settings(DEBUG=True):
            importlib.reload(root_urls)
            clear_url_caches()
            self.assert_video_files_not_served()
