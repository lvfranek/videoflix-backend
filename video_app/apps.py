from django.apps import AppConfig


class VideoAppConfig(AppConfig):
    name = 'video_app'

    def ready(self):
        from . import signals  # noqa: F401  (registers the signal receivers)
