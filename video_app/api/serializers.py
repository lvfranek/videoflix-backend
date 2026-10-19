from rest_framework import serializers

from video_app.models import Video


class VideoListSerializer(serializers.ModelSerializer):
    """
    Video metadata for the dashboard, including an absolute thumbnail
    URL.
    """

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (
            'id',
            'created_at',
            'title',
            'description',
            'thumbnail_url',
            'category',
        )

    def get_thumbnail_url(self, video):
        """
        Return the absolute thumbnail URL, or None if there is none yet.
        """
        if not video.thumbnail:
            return None
        return self.context['request'].build_absolute_uri(video.thumbnail.url)
