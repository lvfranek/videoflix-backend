"""Helpers to convert uploaded videos into HLS streams and thumbnails with FFmpeg."""

import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

# Resolution name (as used in the API) -> output height in pixels
HLS_RESOLUTIONS = {'480p': 480, '720p': 720, '1080p': 1080}
HLS_SEGMENT_SECONDS = 10
HLS_PLAYLIST_NAME = 'index.m3u8'

THUMBNAIL_DIRECTORY = 'thumbnails'
THUMBNAIL_WIDTH = 1280

VIDEO_LIST_CACHE_TIMEOUT = 60 * 15
VIDEO_LIST_VERSION_KEY = 'video_list:version'


def get_video_directory(video_id):
    """Return the folder that holds all HLS resolutions of a video."""
    return Path(settings.MEDIA_ROOT) / 'videos' / str(video_id)


def get_hls_directory(video_id, resolution):
    """Return the folder that holds the HLS playlist and segments of one resolution."""
    return get_video_directory(video_id) / resolution


def build_hls_command(source_path, output_directory, height):
    """Build the FFmpeg command that encodes a video into one HLS rendition of the given height."""
    return [
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(source_path),
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-force_key_frames', f'expr:gte(t,n_forced*{HLS_SEGMENT_SECONDS})',
        '-c:a', 'aac', '-b:a', '128k', '-ac', '2',
        '-f', 'hls', '-hls_time', str(HLS_SEGMENT_SECONDS), '-hls_playlist_type', 'vod',
        '-hls_segment_filename', str(output_directory / '%03d.ts'),
        str(output_directory / HLS_PLAYLIST_NAME),
    ]


def convert_to_hls(source_path, video_id, resolution):
    """Encode the source video into one HLS resolution and return the playlist path."""
    output_directory = get_hls_directory(video_id, resolution)
    output_directory.mkdir(parents=True, exist_ok=True)
    command = build_hls_command(source_path, output_directory, HLS_RESOLUTIONS[resolution])
    subprocess.run(command, check=True, capture_output=True)
    return output_directory / HLS_PLAYLIST_NAME


def convert_to_all_resolutions(source_path, video_id):
    """Encode the source video into every supported HLS resolution."""
    for resolution in HLS_RESOLUTIONS:
        convert_to_hls(source_path, video_id, resolution)


def build_thumbnail_command(source_path, output_path):
    """Build the FFmpeg command that saves the most representative early frame as JPEG."""
    return [
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(source_path),
        '-vf', f'thumbnail,scale={THUMBNAIL_WIDTH}:-2',
        '-frames:v', '1', '-q:v', '3',
        str(output_path),
    ]


def generate_thumbnail(source_path, video_id):
    """Create a thumbnail from a video frame and return its path relative to MEDIA_ROOT."""
    relative_path = f'{THUMBNAIL_DIRECTORY}/{video_id}.jpg'
    output_path = Path(settings.MEDIA_ROOT) / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_thumbnail_command(source_path, output_path), check=True, capture_output=True)
    return relative_path


def ensure_thumbnail(video):
    """Generate a thumbnail for the video unless the admin already uploaded one."""
    if video.thumbnail:
        return
    video.thumbnail.name = generate_thumbnail(video.video_file.path, video.pk)
    video.save(update_fields=['thumbnail'])


def delete_video_files(video, video_id):
    """
    Remove the original upload, the thumbnail and all HLS streams of a video from disk.

    The id is passed separately because Django resets `video.pk` to None after deletion.
    """
    video.video_file.delete(save=False)
    video.thumbnail.delete(save=False)
    shutil.rmtree(get_video_directory(video_id), ignore_errors=True)


def get_video_list_cache_key(base_url):
    """
    Return the cache key of the video list for one base URL.

    The key contains the base URL because the thumbnail URLs are absolute, and a
    version number so that one increment invalidates the list for every host.
    """
    version = cache.get_or_set(VIDEO_LIST_VERSION_KEY, 1, timeout=None)
    return f'video_list:v{version}:{base_url}'


def invalidate_video_list_cache():
    """Make every cached video list outdated after videos were added, changed or removed."""
    try:
        cache.incr(VIDEO_LIST_VERSION_KEY)
    except ValueError:
        cache.set(VIDEO_LIST_VERSION_KEY, 1, timeout=None)
