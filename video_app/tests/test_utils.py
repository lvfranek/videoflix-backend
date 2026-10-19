import shutil
import subprocess
from unittest import skipUnless

from video_app.utils import (
    HLS_RESOLUTIONS,
    build_hls_command,
    convert_to_all_resolutions,
    generate_thumbnail,
    get_hls_directory,
)

from .helpers import VideoTestCase

TEST_VIDEO_COMMAND = (
    'ffmpeg -loglevel error -f lavfi '
    '-i testsrc=duration=2:size=320x180:rate=25 -pix_fmt yuv420p'
).split()


class BuildHlsCommandTests(VideoTestCase):
    """Tests for the FFmpeg command that creates one HLS resolution."""

    def setUp(self):
        super().setUp()
        self.command = build_hls_command('source.mp4', self.media_root, 720)

    def option(self, name):
        return self.command[self.command.index(name) + 1]

    def test_scales_to_requested_height_keeping_aspect_ratio(self):
        self.assertEqual(self.option('-vf'), 'scale=-2:720')

    def test_writes_ten_second_segments_named_like_000_ts(self):
        self.assertEqual(self.option('-hls_time'), '10')
        self.assertTrue(
            self.option('-hls_segment_filename').endswith('%03d.ts')
        )
        self.assertTrue(self.command[-1].endswith('index.m3u8'))

    def test_does_not_require_an_audio_track(self):
        self.assertNotIn('-map', self.command)


@skipUnless(shutil.which('ffmpeg'), 'FFmpeg is not installed')
class RealFfmpegTests(VideoTestCase):
    """
    Integration tests that run the real FFmpeg on a tiny generated
    video.
    """

    def setUp(self):
        super().setUp()
        self.source = self.media_root / 'source.mp4'
        subprocess.run([*TEST_VIDEO_COMMAND, str(self.source)], check=True)

    def test_converts_silent_video_into_all_resolutions(self):
        convert_to_all_resolutions(self.source, video_id=1)
        for resolution in HLS_RESOLUTIONS:
            with self.subTest(resolution=resolution):
                folder = get_hls_directory(1, resolution)
                self.assertTrue((folder / 'index.m3u8').is_file())
                self.assertTrue((folder / '000.ts').is_file())

    def test_generates_jpeg_thumbnail(self):
        relative_path = generate_thumbnail(self.source, video_id=1)
        self.assertEqual(relative_path, 'thumbnails/1.jpg')
        self.assertTrue(
            (self.media_root / relative_path)
            .read_bytes()
            .startswith(b'\xff\xd8')
        )
