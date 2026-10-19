from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Admin view to upload videos and follow their conversion status."""

    list_display = ('title', 'category', 'status', 'created_at')
    list_filter = ('category', 'status')
    search_fields = ('title', 'description')
    readonly_fields = ('status', 'created_at')
    fields = ('title', 'description', 'category', 'video_file', 'thumbnail', 'status', 'created_at')
