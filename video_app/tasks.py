"""
Background jobs of the video app, executed by the django-rq worker.

Video jobs get a timeout of one hour, because converting long videos
into three resolutions can take a while.
"""

import subprocess

import django_rq
from django.db import transaction

from .models import Video
from .utils import convert_to_all_resolutions, ensure_thumbnail

VIDEO_JOB_TIMEOUT = 60 * 60


def process_video(video_id):
    """
    Create the thumbnail and HLS streams of an uploaded video while
    tracking its status.
    """
    video = Video.objects.filter(pk=video_id).first()
    if video is None:
        return
    video.set_status(Video.Status.PROCESSING)
    try:
        ensure_thumbnail(video)
        convert_to_all_resolutions(video.video_file.path, video.pk)
    except (subprocess.CalledProcessError, OSError):
        video.set_status(Video.Status.FAILED)
        raise
    video.set_status(Video.Status.READY)


def queue_video_processing(video):
    """
    Queue the video conversion once the upload is committed to the
    database.
    """
    transaction.on_commit(
        lambda: django_rq.enqueue(
            process_video, video.pk, job_timeout=VIDEO_JOB_TIMEOUT
        )
    )


def generate_missing_thumbnail(video_id):
    """Create a new thumbnail for a video that lost its thumbnail."""
    video = Video.objects.filter(pk=video_id).first()
    if video is not None:
        ensure_thumbnail(video)


def queue_thumbnail_generation(video):
    """Queue a new thumbnail once the change is committed."""
    transaction.on_commit(
        lambda: django_rq.enqueue(generate_missing_thumbnail, video.pk)
    )
