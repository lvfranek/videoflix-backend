from importlib import import_module

from django.apps import AppConfig


class VideoAppConfig(AppConfig):
    """App config of the video app; registers its signal receivers."""

    name = 'video_app'

    def ready(self):
        import_module('video_app.signals')
