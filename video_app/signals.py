from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Video
from .tasks import queue_video_processing


@receiver(post_save, sender=Video)
def process_uploaded_video(sender, instance, created, **kwargs):
    """Start the background conversion as soon as a new video has been uploaded."""
    if created:
        queue_video_processing(instance)
