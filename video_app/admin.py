from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """
    Admin view to upload videos and follow their conversion status.
    """

    list_display = ('title', 'category', 'status', 'created_at')
    list_filter = ('category', 'status')
    search_fields = ('title', 'description')
    readonly_fields = ('status', 'created_at')
    fields = (
        'title',
        'description',
        'category',
        'video_file',
        'thumbnail',
        'status',
        'created_at',
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Lock the video file after upload; a different video needs a new
        entry.
        """
        if obj is None:
            return self.readonly_fields
        return self.readonly_fields + ('video_file',)
