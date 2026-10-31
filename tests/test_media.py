from __future__ import annotations

import shutil
import struct
import tempfile
import unittest
import zlib
from dataclasses import replace
from pathlib import Path

from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.core.jobs import create_job
from geofactory.media.asset_manager import register_asset
from geofactory.media.tts_engine import (
    TTSError, _validate_audio_chunk, audio_duration_seconds, split_sentences,
    synthesize,
)
from geofactory.media.video_editor import probe_video, render_video
from geofactory.quality.qa_engine import validate_srt


MEDIA_TOOLS = all(shutil.which(tool) for tool in ("espeak-ng", "ffmpeg", "ffprobe"))


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data)) + kind + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _write_test_png(path: Path) -> None:
    header = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    pixels = b"\x00" + bytes((90, 130, 170)) * 2 + b"\x00" + bytes((180, 150, 100)) * 2
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(pixels))
        + _png_chunk(b"IEND", b"")
    )


class MediaIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / "factory.sqlite3")
        self.database.initialize()
        self.config = FactoryConfig(
            root=self.root,
            database_path=self.root / "factory.sqlite3",
            output_dir=self.root / "output",
            minimum_free_disk_gb=0,
            width=320,
            height=180,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sentence_chunking_keeps_text_and_bounds_chunks(self) -> None:
        chunks = split_sentences("First sentence. " + "A longer phrase, " * 20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))
        self.assertIn("First sentence.", chunks[0])

    @unittest.skipUnless(MEDIA_TOOLS, "eSpeak NG and FFmpeg/FFprobe are required")
    def test_espeak_generates_measured_audio_and_synchronized_srt(self) -> None:
        config = replace(self.config, tts_backend="espeak-ng")
        audio = self.root / "narration.wav"
        subtitles = self.root / "subtitles.srt"
        duration = synthesize(
            "This is a local narration test. It checks measured captions.",
            audio,
            config,
            subtitles,
        )
        self.assertGreater(duration, 0.5)
        self.assertAlmostEqual(audio_duration_seconds(audio), duration, delta=0.1)
        self.assertEqual(validate_srt(subtitles), [])
        last_end = subtitles.read_text(encoding="utf-8").strip().splitlines()[-2].split(" --> ")[1]
        self.assertAlmostEqual(duration, _timestamp_seconds(last_end), delta=0.02)

    @unittest.skipUnless(MEDIA_TOOLS, "FFmpeg/FFprobe are required")
    def test_nearly_silent_audio_chunk_is_rejected(self) -> None:
        import subprocess

        silent_audio = self.root / "silent.wav"
        result = subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg", "-v", "error", "-f", "lavfi",
                "-i", "anullsrc=channel_layout=mono:sample_rate=22050", "-t", "0.5",
                "-c:a", "pcm_s16le", str(silent_audio),
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaises(TTSError):
            _validate_audio_chunk(silent_audio, self.config)

    @unittest.skipUnless(MEDIA_TOOLS, "eSpeak NG and FFmpeg/FFprobe are required")
    def test_ffmpeg_render_contains_video_audio_and_soft_subtitles(self) -> None:
        config = replace(self.config, tts_backend="espeak-ng")
        job = create_job(
            self.database, "Synthetic media test", "Does the local render work?",
            self.config.output_dir,
        )
        package = Path(job["output_dir"])
        package.mkdir(parents=True, exist_ok=True)
        image = self.root / "illustrative-test.png"
        _write_test_png(image)
        asset_id = register_asset(
            self.database, job["id"], image, "https://example.invalid/test-image",
            "Synthetic fixture", "CC0-1.0", "Synthetic fixture, CC0-1.0", True,
        )
        with self.database.connect() as conn:
            asset = dict(conn.execute(
                "SELECT * FROM assets WHERE id = ?", (asset_id,)
            ).fetchone())
        narration = package / "narration.wav"
        subtitles = package / "subtitles.srt"
        synthesize(
            "This is an explicitly synthetic rendering test.",
            narration, config, subtitles,
        )
        result = render_video(
            config, [image], narration, package / "final.mp4", [asset], subtitles,
        )
        streams = probe_video(config, result)["streams"]
        kinds = {stream["codec_type"] for stream in streams}
        self.assertTrue({"video", "audio", "subtitle"}.issubset(kinds))
        video = next(stream for stream in streams if stream["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (320, 180))
        self.assertEqual(validate_srt(subtitles), [])


def _timestamp_seconds(timestamp: str) -> float:
    hours, minutes, remainder = timestamp.split(":")
    seconds, millis = remainder.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


if __name__ == "__main__":
    unittest.main()
