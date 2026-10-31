from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from geofactory.agents.groq_client import GroqGenerationError, generate_json
from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.core.jobs import create_job
from geofactory.media.asset_manager import (
    AssetRightsError, register_music_asset, search_and_download_stock_videos,
)
from geofactory.media.tts_engine import _synthesize_edge_chunk, audio_duration_seconds

MEDIA_TOOLS = all(shutil.which(name) for name in ("ffmpeg", "ffprobe"))


class ProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "factory.sqlite3")
        self.db.initialize()
        self.job = create_job(
            self.db, "Synthetic provider test", "Does provider integration work?",
            self.root / "output",
        )
        self.config = FactoryConfig(
            root=self.root,
            database_path=self.root / "factory.sqlite3",
            output_dir=self.root / "output",
            pexels_api_key="test-pexels-key",
            pixabay_api_key="test-pixabay-key",
            groq_api_key="test-groq-secret",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_api_keys_are_not_in_config_repr_or_missing_key_errors(self) -> None:
        self.assertNotIn("test-groq-secret", repr(self.config))
        with self.assertRaisesRegex(AssetRightsError, "not configured"):
            search_and_download_stock_videos(
                self.db, self.job["id"], "Tokyo", self.root / "assets",
                replace(self.config, pexels_api_key=""),
                provider="pexels",
            )

    def test_pexels_and_pixabay_results_are_registered_as_licensed_video(self) -> None:
        fixtures = {
            "pexels": {
                "videos": [{
                    "id": 123,
                    "url": "https://www.pexels.com/video/tokyo-123/",
                    "user": {"name": "Synthetic Creator"},
                    "video_files": [{
                        "file_type": "video/mp4",
                        "width": 1280,
                        "link": "https://videos.pexels.com/video-files/123/clip.mp4",
                    }],
                }]
            },
            "pixabay": {
                "hits": [{
                    "pageURL": "https://pixabay.com/videos/tokyo-city-123/",
                    "user": "Synthetic Creator",
                    "tags": "tokyo,city",
                    "videos": {
                        "large": {"url": "https://cdn.pixabay.com/video/2026/clip.mp4"}
                    },
                }]
            },
        }
        for provider, response in fixtures.items():
            with self.subTest(provider=provider):
                fake_video = self.root / f"{provider}.mp4"
                fake_video.write_bytes(
                    b"\x00\x00\x00\x18ftypisom" + provider.encode("ascii")
                )
                digest = hashlib.sha256(fake_video.read_bytes()).hexdigest()
                with (
                    patch(
                        "geofactory.media.asset_manager._provider_json",
                        return_value=response,
                    ),
                    patch(
                        "geofactory.media.asset_manager._download_stock_video",
                        return_value=(fake_video, digest),
                    ),
                    patch("geofactory.media.asset_manager._validate_mp4"),
                ):
                    result = search_and_download_stock_videos(
                        self.db, self.job["id"], "Tokyo city geography",
                        self.root / "assets", self.config, provider=provider,
                    )
                self.assertEqual(len(result["assets"]), 1)
                self.assertEqual(result["assets"][0]["media_type"], "video")
                self.assertEqual(result["assets"][0]["licence"], {
                    "pexels": "Pexels License",
                    "pixabay": "Pixabay Content License",
                }[provider])
                self.assertIn("Synthetic Creator", result["assets"][0]["attribution"])

    @unittest.skipUnless(MEDIA_TOOLS, "FFmpeg/FFprobe are required")
    def test_owner_music_registration_requires_and_records_audio_rights(self) -> None:
        audio = self.root / "theme.wav"
        generated = subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg", "-v", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:sample_rate=22050", "-t", "0.5",
                "-c:a", "pcm_s16le", str(audio),
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        asset_id = register_music_asset(
            self.db, self.job["id"], audio,
            "https://pixabay.com/music/synthetic-fixture/",
            "Synthetic test creator", "Pixabay Content License",
            "Synthetic test creator, test music, Pixabay Content License",
            True, title="Synthetic test music", publisher="Pixabay",
        )
        with self.db.connect() as conn:
            asset = dict(conn.execute(
                "SELECT media_type, licence, publisher FROM assets WHERE id=?",
                (asset_id,),
            ).fetchone())
        self.assertEqual(asset, {
            "media_type": "audio",
            "licence": "Pixabay Content License",
            "publisher": "Pixabay",
        })

    def test_groq_client_returns_json_and_never_logs_credentials(self) -> None:
        calls: dict[str, object] = {}

        class FakeCompletions:
            def create(self, **kwargs):
                calls.update(kwargs)
                return types.SimpleNamespace(choices=[
                    types.SimpleNamespace(message=types.SimpleNamespace(content='{"ok": true}'))
                ])

        fake_client = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=FakeCompletions())
        )
        fake_module = types.ModuleType("groq")
        fake_module.Groq = lambda **kwargs: (
            calls.update({"client_args": kwargs}) or fake_client
        )
        with patch.dict(sys.modules, {"groq": fake_module}):
            result = generate_json(self.config, "Write a test response.")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["model"], self.config.groq_model)
        self.assertNotIn("test-groq-secret", repr(self.config))

        class FailingCompletions:
            def create(self, **kwargs):
                raise RuntimeError("request failed for test-groq-secret")

        fake_module.Groq = lambda **kwargs: types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=FailingCompletions())
        )
        with patch.dict(sys.modules, {"groq": fake_module}):
            with self.assertRaises(GroqGenerationError) as raised:
                generate_json(self.config, "Write a test response.")
        self.assertNotIn("test-groq-secret", str(raised.exception))

    @unittest.skipUnless(MEDIA_TOOLS, "FFmpeg/FFprobe are required")
    def test_edge_tts_chunk_is_converted_to_verified_wav(self) -> None:
        source_mp3 = self.root / "fixture.mp3"
        generated = subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg", "-v", "error", "-f", "lavfi",
                "-i", "sine=frequency=660:sample_rate=22050", "-t", "0.5",
                "-c:a", "libmp3lame", str(source_mp3),
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)

        class FakeCommunicate:
            def __init__(self, text: str, voice: str) -> None:
                self.voice = voice

            async def save(self, path: str) -> None:
                Path(path).write_bytes(source_mp3.read_bytes())

        fake_module = types.ModuleType("edge_tts")
        fake_module.Communicate = FakeCommunicate
        destination = self.root / "chunk.wav"
        with patch.dict(sys.modules, {"edge_tts": fake_module}):
            _synthesize_edge_chunk("Synthetic voice test.", destination, self.config)
        self.assertGreater(audio_duration_seconds(destination), 0.4)
        self.assertFalse(destination.with_suffix(".mp3").exists())


if __name__ == "__main__":
    unittest.main()
