from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Video
from .tasks import queue_thumbnail_generation, queue_video_processing
from .utils import delete_video_files, invalidate_video_list_cache


@receiver(post_save, sender=Video)
def process_uploaded_video(sender, instance, created, **kwargs):
    """
    Start the background conversion as soon as a new video has been
    uploaded.
    """
    if created:
        queue_video_processing(instance)


@receiver(post_save, sender=Video)
def restore_removed_thumbnail(sender, instance, created, **kwargs):
    """
    Generate a new thumbnail when the thumbnail of a ready video was
    removed, so the frontend never shows a broken image.
    """
    is_ready = instance.status == Video.Status.READY
    if not created and is_ready and not instance.thumbnail:
        queue_thumbnail_generation(instance)


@receiver(post_delete, sender=Video)
def remove_files_of_deleted_video(sender, instance, **kwargs):
    """
    Delete all media files of a video once its database entry is gone
    for good.
    """
    video_id = instance.pk
    transaction.on_commit(lambda: delete_video_files(instance, video_id))


@receiver([post_save, post_delete], sender=Video)
def refresh_cached_video_list(sender, **kwargs):
    """
    Drop the cached video list whenever a video is created, edited or
    deleted.
    """
    invalidate_video_list_cache()
