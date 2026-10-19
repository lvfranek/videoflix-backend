from django.urls import reverse
from rest_framework import status

from video_app.models import Video

from .helpers import (
    VideoTestCase,
    authenticate,
    create_hls_files,
    create_video,
)


class HlsTestCase(VideoTestCase):
    """Provides a logged-in client and a ready video with HLS files."""

    def setUp(self):
        super().setUp()
        authenticate(self.client)
        self.video = create_video()
        create_hls_files(self.video)

    def get_content(self, response):
        return b''.join(response.streaming_content)


class HlsPlaylistTests(HlsTestCase):
    """Tests for GET /api/video/<movie_id>/<resolution>/index.m3u8."""

    def playlist_url(self, movie_id=None, resolution='720p'):
        return reverse(
            'video-playlist', args=[movie_id or self.video.pk, resolution]
        )

    def test_returns_playlist_for_every_resolution(self):
        for resolution in ('480p', '720p', '1080p'):
            with self.subTest(resolution=resolution):
                response = self.client.get(
                    self.playlist_url(resolution=resolution)
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response['Content-Type'], 'application/vnd.apple.mpegurl'
                )
                self.assertTrue(
                    self.get_content(response).startswith(b'#EXTM3U')
                )

    def test_requires_authentication(self):
        self.client.cookies.clear()
        response = self.client.get(self.playlist_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_resolution_or_video_returns_404(self):
        for url in (
            self.playlist_url(resolution='4k'),
            self.playlist_url(movie_id=9999),
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code, status.HTTP_404_NOT_FOUND
                )

    def test_video_that_is_not_ready_returns_404(self):
        self.video.set_status(Video.Status.PROCESSING)
        response = self.client.get(self.playlist_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_playlist_file_returns_404(self):
        video_without_files = create_video(title='No files')
        response = self.client.get(
            self.playlist_url(movie_id=video_without_files.pk)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HlsSegmentTests(HlsTestCase):
    """Tests for GET /api/video/<movie_id>/<resolution>/<segment>/."""

    def segment_url(self, segment='000.ts', with_slash=True):
        url_name = (
            'video-segment' if with_slash else 'video-segment-without-slash'
        )
        return reverse(url_name, args=[self.video.pk, '720p', segment])

    def test_returns_segment_with_and_without_trailing_slash(self):
        for with_slash in (True, False):
            with self.subTest(with_slash=with_slash):
                response = self.client.get(
                    self.segment_url(with_slash=with_slash)
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response['Content-Type'], 'video/MP2T')
                self.assertEqual(self.get_content(response), b'segment')

    def test_segment_url_without_slash_matches_playlist_entries(self):
        self.assertTrue(
            self.segment_url(with_slash=False).endswith('/720p/000.ts')
        )

    def test_requires_authentication(self):
        self.client.cookies.clear()
        response = self.client.get(self.segment_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_or_missing_segments_return_404(self):
        for segment in ('099.ts', 'clip.mp4', 'index.m3u8'):
            with self.subTest(segment=segment):
                response = self.client.get(self.segment_url(segment=segment))
                self.assertEqual(
                    response.status_code, status.HTTP_404_NOT_FOUND
                )
