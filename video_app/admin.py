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

    def save_model(self, request, obj, form, change):
        """
        Save the video and delete the file of a replaced or removed
        thumbnail, so no unused images stay on disk.
        """
        previous_thumbnail = form.initial.get('thumbnail')
        super().save_model(request, obj, form, change)
        if change and 'thumbnail' in form.changed_data and previous_thumbnail:
            previous_thumbnail.storage.delete(previous_thumbnail.name)
