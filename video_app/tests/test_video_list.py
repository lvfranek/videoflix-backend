from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from video_app.models import Video

from .helpers import VideoTestCase, authenticate, create_video


class VideoListTests(VideoTestCase):
    """Tests for GET /api/video/."""

    url = reverse('video-list')

    def setUp(self):
        super().setUp()
        authenticate(self.client)

    def test_requires_authentication(self):
        self.client.cookies.clear()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def expected_item(self, video):
        return {
            'id': video.id,
            'created_at': video.created_at.isoformat().replace('+00:00', 'Z'),
            'title': 'Test Video',
            'description': 'A test video.',
            'thumbnail_url': 'http://testserver/media/thumbnails/thumb.jpg',
            'category': 'Drama',
        }

    def test_returns_documented_fields(self):
        video = create_video(thumbnail=SimpleUploadedFile('thumb.jpg', b'jpg'))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [self.expected_item(video)])

    def test_thumbnail_url_is_null_without_thumbnail(self):
        create_video()
        self.assertIsNone(self.client.get(self.url).json()[0]['thumbnail_url'])

    def test_videos_are_sorted_newest_first(self):
        now = timezone.now()
        for title, age_in_days in (('Old', 3), ('Newest', 0), ('Middle', 1)):
            video = create_video(title=title)
            Video.objects.filter(pk=video.pk).update(
                created_at=now - timedelta(days=age_in_days)
            )
        titles = [video['title'] for video in self.client.get(self.url).json()]
        self.assertEqual(titles, ['Newest', 'Middle', 'Old'])

    def test_only_ready_videos_are_listed(self):
        create_video(title='Ready')
        for unfinished_status in (
            Video.Status.PENDING,
            Video.Status.PROCESSING,
            Video.Status.FAILED,
        ):
            create_video(title=unfinished_status, status=unfinished_status)
        titles = [video['title'] for video in self.client.get(self.url).json()]
        self.assertEqual(titles, ['Ready'])

    def test_second_request_is_served_from_cache(self):
        create_video()
        self.client.get(self.url)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url)
        self.assertEqual(len(response.json()), 1)
        self.assertFalse(
            [query for query in queries if 'video_app_video' in query['sql']]
        )

    def test_changes_are_visible_despite_cache(self):
        video = create_video()
        self.client.get(self.url)
        video.title = 'Renamed'
        video.save()
        self.assertEqual(
            self.client.get(self.url).json()[0]['title'], 'Renamed'
        )
