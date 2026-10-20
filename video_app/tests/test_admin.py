from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .helpers import VideoTestCase, create_video

ENQUEUE = 'video_app.tasks.django_rq.enqueue'


class VideoAdminThumbnailTests(VideoTestCase):
    """Changing the thumbnail in the admin leaves no unused files."""

    def setUp(self):
        super().setUp()
        admin_user = get_user_model().objects.create_superuser(
            username='admin', email='admin@example.com', password=None
        )
        self.client.force_login(admin_user)
        thumbnail = SimpleUploadedFile('own.jpg', b'jpg')
        self.video = create_video(thumbnail=thumbnail)
        self.old_file = Path(self.video.thumbnail.path)

    def change_thumbnail(self, **thumbnail_data):
        url = reverse('admin:video_app_video_change', args=[self.video.pk])
        form = {'title': 'Test Video', 'description': '-', 'category': 'Drama'}
        with patch(ENQUEUE), self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, {**form, **thumbnail_data})

    def test_replacing_thumbnail_deletes_the_old_file(self):
        new_thumbnail = SimpleUploadedFile('new.jpg', b'new')
        self.change_thumbnail(thumbnail=new_thumbnail)
        self.video.refresh_from_db()
        self.assertEqual(self.video.thumbnail.name, 'thumbnails/new.jpg')
        self.assertFalse(self.old_file.exists())

    def test_clearing_thumbnail_deletes_file_and_queues_new_one(self):
        with patch('video_app.signals.queue_thumbnail_generation') as queue:
            self.change_thumbnail(**{'thumbnail-clear': 'on'})
        self.assertFalse(self.old_file.exists())
        queue.assert_called_once()

    def test_editing_other_fields_keeps_the_thumbnail(self):
        self.change_thumbnail()
        self.video.refresh_from_db()
        self.assertEqual(self.video.thumbnail.name, 'thumbnails/own.jpg')
        self.assertTrue(self.old_file.exists())
