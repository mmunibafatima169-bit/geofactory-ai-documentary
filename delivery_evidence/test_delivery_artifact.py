#!/usr/bin/env python3
"""Media release-gate tests for the supplied v2 artifact (stdlib only)."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "examples/studio-sample-v2/venice_sample_60s_v2.mp4"
SRT = ROOT / "examples/studio-sample-v2/subtitles.srt"
BIN = ROOT / "studio/remotion/node_modules"
FFMPEG = BIN / "@ffmpeg-installer/linux-x64/ffmpeg"
FFPROBE = BIN / "@ffprobe-installer/linux-x64/ffprobe"


def run(args):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, check=False)


class DeliveryArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", VIDEO])
        cls.meta = json.loads(cls.probe.stdout)
        cls.video = next(s for s in cls.meta["streams"] if s["codec_type"] == "video")
        cls.audio = next(s for s in cls.meta["streams"] if s["codec_type"] == "audio")
        cls.subtitle = next(s for s in cls.meta["streams"] if s["codec_type"] == "subtitle")

    def test_01_probe_succeeds(self):
        self.assertEqual(self.probe.returncode, 0, self.probe.stderr)

    def test_02_duration_is_60_seconds(self):
        self.assertAlmostEqual(float(self.meta["format"]["duration"]), 60.0, places=3)

    def test_03_video_is_1080p30_h264(self):
        self.assertEqual((self.video["width"], self.video["height"]), (1920, 1080))
        self.assertEqual(self.video["avg_frame_rate"], "30/1")
        self.assertEqual(self.video["codec_name"], "h264")

    def test_04_aspect_and_pixel_format(self):
        self.assertEqual(self.video["display_aspect_ratio"], "16:9")
        self.assertEqual(self.video["sample_aspect_ratio"], "1:1")
        self.assertEqual(self.video["pix_fmt"], "yuv420p")

    def test_05_audio_is_48khz_stereo_aac(self):
        self.assertEqual(self.audio["codec_name"], "aac")
        self.assertEqual(self.audio["sample_rate"], "48000")
        self.assertEqual(self.audio["channels"], 2)

    def test_06_av_container_duration_delta_below_20ms(self):
        delta = abs(float(self.video["duration"]) - float(self.audio["duration"]))
        self.assertLess(delta, 0.020)

    def test_07_english_soft_subtitles_exist(self):
        self.assertEqual(self.subtitle["codec_name"], "mov_text")
        self.assertEqual(self.subtitle["tags"]["language"], "eng")

    def test_08_srt_syntax_bounds_and_length(self):
        text = SRT.read_text(encoding="utf-8").strip()
        cues = re.findall(r"(\d+)\n(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})\n(.*?)(?=\n\n|\Z)", text, re.S)
        self.assertEqual(len(cues), 22)
        self.assertEqual([int(c[0]) for c in cues], list(range(1, 23)))
        self.assertTrue(all(len(c[3].replace("\n", " ")) <= 84 for c in cues))

    def test_09_full_decode_has_no_errors(self):
        result = run([FFMPEG, "-v", "error", "-xerror", "-i", VIDEO, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_10_no_black_interval_at_100ms_threshold(self):
        result = run([FFMPEG, "-hide_banner", "-i", VIDEO, "-vf", "blackdetect=d=0.10:pix_th=0.02", "-an", "-f", "null", "-"])
        self.assertNotIn("black_start:", result.stderr)

    def test_11_no_freeze_interval_at_500ms_threshold(self):
        result = run([FFMPEG, "-hide_banner", "-i", VIDEO, "-vf", "freezedetect=n=-50dB:d=0.50", "-an", "-f", "null", "-"])
        self.assertNotIn("freeze_start:", result.stderr, "Static/frozen holds detected; inspect black_freeze_decode.log")

    def test_12_audio_peak_below_minus_1dbtp(self):
        result = run([FFMPEG, "-hide_banner", "-i", VIDEO, "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"])
        summary = result.stderr.rsplit("Summary:", 1)[-1]
        match = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
        self.assertIsNotNone(match)
        self.assertLess(float(match.group(1)), -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
