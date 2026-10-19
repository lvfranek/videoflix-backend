from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Video
from .tasks import queue_video_processing
from .utils import delete_video_files


@receiver(post_save, sender=Video)
def process_uploaded_video(sender, instance, created, **kwargs):
    """Start the background conversion as soon as a new video has been uploaded."""
    if created:
        queue_video_processing(instance)


@receiver(post_delete, sender=Video)
def remove_files_of_deleted_video(sender, instance, **kwargs):
    """Delete all media files of a video once its database entry is gone for good."""
    video_id = instance.pk
    transaction.on_commit(lambda: delete_video_files(instance, video_id))
