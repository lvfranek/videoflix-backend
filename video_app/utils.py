"""Helpers to convert uploaded videos into HLS streams with FFmpeg."""

import subprocess
from pathlib import Path

from django.conf import settings

# Resolution name (as used in the API) -> output height in pixels
HLS_RESOLUTIONS = {'480p': 480, '720p': 720, '1080p': 1080}
HLS_SEGMENT_SECONDS = 10
HLS_PLAYLIST_NAME = 'index.m3u8'


def get_hls_directory(video_id, resolution):
    """Return the folder that holds the HLS playlist and segments of one resolution."""
    return Path(settings.MEDIA_ROOT) / 'videos' / str(video_id) / resolution


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
