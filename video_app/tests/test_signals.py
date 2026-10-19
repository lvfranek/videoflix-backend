from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from video_app.models import Video
from video_app.tasks import VIDEO_JOB_TIMEOUT, process_video
from video_app.utils import get_video_directory, get_video_list_cache_key

from .helpers import VideoTestCase, create_hls_files, create_video

ENQUEUE = 'video_app.tasks.django_rq.enqueue'


class UploadSignalTests(VideoTestCase):
    """A new upload starts the background conversion exactly once."""

    def test_upload_queues_processing_job_after_commit(self):
        with patch(ENQUEUE) as enqueue, self.captureOnCommitCallbacks(execute=True):
            video = Video.objects.create(
                title='New', description='-', category=Video.Category.ACTION,
                video_file=SimpleUploadedFile('new.mp4', b'video', content_type='video/mp4'),
            )
        enqueue.assert_called_once_with(process_video, video.pk, job_timeout=VIDEO_JOB_TIMEOUT)

    def test_editing_a_video_does_not_queue_it_again(self):
        video = create_video()
        with patch(ENQUEUE) as enqueue, self.captureOnCommitCallbacks(execute=True):
            video.title = 'Renamed'
            video.save()
        enqueue.assert_not_called()


class DeleteSignalTests(VideoTestCase):
    """Deleting a video removes every file that belongs to it."""

    def setUp(self):
        super().setUp()
        self.video = create_video(thumbnail=SimpleUploadedFile('thumb.jpg', b'jpg'))
        create_hls_files(self.video)
        self.files = [Path(self.video.video_file.path), Path(self.video.thumbnail.path)]
        self.hls_directory = get_video_directory(self.video.pk)

    def assert_all_files_removed(self):
        for file_path in self.files:
            self.assertFalse(file_path.exists(), file_path)
        self.assertFalse(self.hls_directory.exists())

    def test_single_delete_removes_original_thumbnail_and_hls_files(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.video.delete()
        self.assert_all_files_removed()

    def test_bulk_delete_removes_files_as_well(self):
        with self.captureOnCommitCallbacks(execute=True):
            Video.objects.all().delete()
        self.assert_all_files_removed()

    def test_other_videos_keep_their_files(self):
        other_video = create_video(title='Other')
        create_hls_files(other_video)
        with self.captureOnCommitCallbacks(execute=True):
            self.video.delete()
        self.assertTrue(Path(other_video.video_file.path).exists())
        self.assertTrue(get_video_directory(other_video.pk).exists())


class CacheInvalidationTests(VideoTestCase):
    """Every change to a video makes the cached video list outdated."""

    def assert_cache_key_changes(self, change):
        key_before = get_video_list_cache_key('http://testserver/')
        change()
        self.assertNotEqual(get_video_list_cache_key('http://testserver/'), key_before)

    def test_upload_invalidates_cached_list(self):
        self.assert_cache_key_changes(create_video)

    def test_edit_invalidates_cached_list(self):
        video = create_video()
        self.assert_cache_key_changes(video.save)

    def test_status_change_invalidates_cached_list(self):
        video = create_video(status=Video.Status.PROCESSING)
        self.assert_cache_key_changes(lambda: video.set_status(Video.Status.READY))

    def test_delete_invalidates_cached_list(self):
        video = create_video()
        self.assert_cache_key_changes(video.delete)
