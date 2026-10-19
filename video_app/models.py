from django.core.validators import FileExtensionValidator
from django.db import models

from .utils import invalidate_video_list_cache

VIDEO_EXTENSIONS = ['mp4', 'mov', 'mkv', 'webm', 'avi']
THUMBNAIL_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']


class Video(models.Model):
    """
    A video uploaded by an admin.

    The original file is converted into HLS streams (480p, 720p, 1080p)
    in the background; `status` tracks that conversion.
    """

    class Category(models.TextChoices):
        ACTION = 'Action'
        COMEDY = 'Comedy'
        DOCUMENTARY = 'Documentary'
        DRAMA = 'Drama'
        HORROR = 'Horror'
        ROMANCE = 'Romance'
        SCI_FI = 'Sci-Fi'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=Category.choices)
    video_file = models.FileField(
        upload_to='videos/originals/',
        max_length=255,
        validators=[FileExtensionValidator(VIDEO_EXTENSIONS)],
    )
    thumbnail = models.FileField(
        upload_to='thumbnails/',
        max_length=255,
        blank=True,
        validators=[FileExtensionValidator(THUMBNAIL_EXTENSIONS)],
        help_text='Leave empty to generate a thumbnail from the video automatically.',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def set_status(self, status):
        """Store a new processing status without triggering save signals again."""
        self.status = status
        Video.objects.filter(pk=self.pk).update(status=status)
        invalidate_video_list_cache()
