import subprocess
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from video_app.models import Video
from video_app.tasks import process_video

from .helpers import VideoTestCase, create_video

FFMPEG_RUN = 'video_app.utils.subprocess.run'


class ProcessVideoTests(VideoTestCase):
    """Tests for the background job that converts an uploaded video."""

    def setUp(self):
        super().setUp()
        self.video = create_video(status=Video.Status.PENDING)

    def test_success_marks_video_ready_with_generated_thumbnail(self):
        with patch(FFMPEG_RUN) as run:
            process_video(self.video.pk)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.READY)
        self.assertEqual(self.video.thumbnail.name, f'thumbnails/{self.video.pk}.jpg')
        self.assertEqual(run.call_count, 4)

    def test_converts_into_all_three_resolutions(self):
        with patch(FFMPEG_RUN) as run:
            process_video(self.video.pk)
        scale_filters = [call.args[0][call.args[0].index('-vf') + 1] for call in run.call_args_list]
        for height in (480, 720, 1080):
            self.assertIn(f'scale=-2:{height}', scale_filters)

    def test_status_is_processing_while_ffmpeg_runs(self):
        statuses_during_run = []

        def record_status(*args, **kwargs):
            statuses_during_run.append(Video.objects.get(pk=self.video.pk).status)

        with patch(FFMPEG_RUN, side_effect=record_status):
            process_video(self.video.pk)
        self.assertEqual(set(statuses_during_run), {Video.Status.PROCESSING})

    def test_uploaded_thumbnail_is_kept(self):
        self.video.thumbnail = SimpleUploadedFile('own.jpg', b'jpg', content_type='image/jpeg')
        self.video.save()
        with patch(FFMPEG_RUN) as run:
            process_video(self.video.pk)
        self.video.refresh_from_db()
        self.assertEqual(self.video.thumbnail.name, 'thumbnails/own.jpg')
        self.assertEqual(run.call_count, 3)

    def test_ffmpeg_error_marks_video_failed_and_is_reported(self):
        error = subprocess.CalledProcessError(1, 'ffmpeg')
        with patch(FFMPEG_RUN, side_effect=error), self.assertRaises(subprocess.CalledProcessError):
            process_video(self.video.pk)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.FAILED)

    def test_video_deleted_before_processing_is_skipped(self):
        with patch(FFMPEG_RUN) as run:
            process_video(9999)
        run.assert_not_called()
