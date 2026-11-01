from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.core.jobs import create_job
from geofactory.media.map_animation_engine import (
    DATASET_LICENSE,
    DATASET_NAME,
    DATASET_VERSION,
    MapAnimationError,
    MapSceneSpec,
    create_map_scene,
    validate_map_scene,
)
from geofactory.media.thumbnail_engine import generate_thumbnail_concepts
from geofactory.media.video_editor import probe_video, render_video
from geofactory.quality.qa_engine import run_qa

MEDIA_TOOLS = all(shutil.which(name) for name in ("ffmpeg", "ffprobe"))

FIXTURE_DATA = {
    "type": "FeatureCollection",
    "name": "ne_110m_admin_0_countries",
    "features": [
        {
            "type": "Feature",
            "properties": {"ADMIN": "Japan", "ISO_A3_EH": "JPN"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [129.0, 31.0], [146.0, 31.0], [146.0, 46.0],
                    [129.0, 46.0], [129.0, 31.0],
                ]],
            },
        },
        {
            "type": "Feature",
            "properties": {"ADMIN": "South Korea", "ISO_A3_EH": "KOR"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [126.0, 34.0], [129.0, 34.0], [129.0, 39.0],
                    [126.0, 39.0], [126.0, 34.0],
                ]],
            },
        },
    ],
}
FIXTURE_MANIFEST = {
    "dataset_name": DATASET_NAME,
    "dataset_version": DATASET_VERSION,
    "licence": DATASET_LICENSE,
    "licence_url": "https://www.naturalearthdata.com/about/terms-of-use/",
    "dataset_url": "fixture",
    "download_date": "2026-11-01",
    "downloaded_at": "2026-11-01T00:00:00+00:00",
    "sha256": "a" * 64,
}


class MapAndThumbnailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_map_scene_records_dataset_and_rejects_tampering(self) -> None:
        if not MEDIA_TOOLS:
            self.skipTest("FFmpeg/FFprobe are required")
        destination = self.root / "map-scene.mp4"
        with patch(
            "geofactory.media.map_animation_engine.load_natural_earth",
            return_value=(FIXTURE_DATA, FIXTURE_MANIFEST),
        ):
            manifest = create_map_scene(
                self.root, destination, MapSceneSpec("JPN", duration_seconds=2),
                width=320, height=180, fps=1,
            )
        self.assertEqual(manifest["dataset_name"], DATASET_NAME)
        self.assertEqual(manifest["dataset_version"], "5.1.1")
        self.assertEqual(manifest["licence"], "Public Domain")
        self.assertEqual(manifest["dataset_download_date"], "2026-11-01")
        self.assertEqual(len(list(destination.with_suffix(".frames").glob("*.png"))), 2)
        self.assertEqual(validate_map_scene(destination)["country_name"], "Japan")
        with destination.open("ab") as stream:
            stream.write(b"tamper")
        with self.assertRaises(MapAnimationError):
            validate_map_scene(destination)

    def test_video_editor_accepts_verified_generated_map_scenes(self) -> None:
        if not MEDIA_TOOLS:
            self.skipTest("FFmpeg/FFprobe are required")
        destination = self.root / "map-scene.mp4"
        with patch(
            "geofactory.media.map_animation_engine.load_natural_earth",
            return_value=(FIXTURE_DATA, FIXTURE_MANIFEST),
        ):
            create_map_scene(
                self.root, destination, MapSceneSpec("JPN", duration_seconds=2),
                width=320, height=180, fps=1,
            )
        ffmpeg = shutil.which("ffmpeg")
        assert ffmpeg is not None
        narration = self.root / "narration.wav"
        audio_result = subprocess.run(
            [
                ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i",
                "sine=frequency=440:sample_rate=22050", "-t", "4",
                "-c:a", "pcm_s16le", str(narration),
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(audio_result.returncode, 0, audio_result.stderr)
        subtitles = self.root / "subtitles.srt"
        subtitles.write_text(
            "1\n00:00:00,000 --> 00:00:04,000\nMap scene and still test.\n",
            encoding="utf-8",
        )
        image = self.root / "nonstandard-aspect.png"
        Image.new("RGB", (777, 521), (40, 90, 130)).save(image)
        asset = {
            "path": str(image),
            "media_type": "image",
            "licence": "Public Domain",
            "commercial_use": True,
            "attribution": "Synthetic fixture",
            "file_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        }
        config = FactoryConfig(
            root=self.root,
            database_path=self.root / "factory.sqlite3",
            output_dir=self.root / "output",
            minimum_free_disk_gb=0,
            width=320,
            height=180,
        )
        rendered = render_video(
            config, [image], narration, self.root / "final.mp4", [asset],
            subtitles, scene_videos=[destination],
        )
        stream_types = {
            stream["codec_type"]
            for stream in probe_video(config, rendered)["streams"]
        }
        self.assertTrue({"video", "audio", "subtitle"}.issubset(stream_types))

    def test_thumbnail_engine_emits_three_distinct_scored_editable_concepts(self) -> None:
        with patch(
            "geofactory.media.thumbnail_engine.load_natural_earth",
            return_value=(FIXTURE_DATA, FIXTURE_MANIFEST),
        ):
            result = generate_thumbnail_concepts(
                "Tokyo geography marvel", "JPN", self.root / "output", self.root
            )
        self.assertEqual(len(result["concepts"]), 3)
        self.assertEqual(len({entry["concept_id"] for entry in result["concepts"]}), 3)
        self.assertTrue(all(entry["scores"]["style_match"] >= 85 for entry in result["concepts"]))
        for entry in result["concepts"]:
            self.assertTrue(entry["measurements"]["layout_variety_pass"])
            self.assertTrue(entry["measurements"]["bottom_right_duration_area_clear"])
            self.assertGreaterEqual(
                entry["measurements"]["headline_block_coverage_fraction"], 0
            )
            self.assertLessEqual(
                entry["measurements"]["headline_block_coverage_fraction"], 1
            )
            low, high = entry["measurements"]["headline_block_coverage_design_range"]
            self.assertLessEqual(
                low,
                entry["measurements"]["headline_block_coverage_fraction"],
            )
            self.assertLessEqual(
                entry["measurements"]["headline_block_coverage_fraction"],
                high,
            )
            self.assertEqual(entry["measurements"]["reference_median_saturation"], 0.519)
            self.assertGreater(
                entry["measurements"]["palette_mean_saturation"], 0
            )
            self.assertTrue((self.root / "output" / entry["image"]).is_file())
            source = json.loads(
                (self.root / "output" / entry["editable_source"]).read_text(encoding="utf-8")
            )
            self.assertTrue(source["no_logo_or_channel_branding"])
            self.assertEqual(source["dataset_version"], "5.1.1")
        with Image.open(result["outputs"]["winner"]) as winner:
            self.assertEqual(winner.size, (1280, 720))
        with Image.open(result["outputs"]["master"]) as master:
            self.assertEqual(master.size, (1920, 1080))
        for entry in result["concepts"]:
            with Image.open(self.root / "output" / entry["image"]) as concept_image:
                self.assertEqual(concept_image.size, (1920, 1080))
            recipe = json.loads(
                (self.root / "output" / entry["editable_source"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(recipe["master_dimensions"], [1920, 1080])
            self.assertEqual(recipe["platform_dimensions"], [1280, 720])
        with Image.open(result["outputs"]["contact_sheet"]) as contact:
            self.assertEqual(contact.size, (1200, 225))
        with Image.open(result["outputs"]["mobile_preview"]) as preview:
            self.assertEqual(preview.size, (160, 90))
        scores = json.loads(
            (self.root / "output" / "thumbnail_scores.json").read_text(encoding="utf-8")
        )
        self.assertIn("style_match", scores["winner_scores"])
        self.assertIn("do not predict views", scores["scoring_notice"])

    def test_qa_reports_map_and_thumbnail_engine_results_actionably(self) -> None:
        if not MEDIA_TOOLS:
            self.skipTest("FFmpeg/FFprobe are required")
        db = Database(self.root / "factory.sqlite3")
        db.initialize()
        job = create_job(
            db, "Tokyo geography marvel", "Why is Tokyo located here?",
            self.root / "output",
        )
        package = Path(job["output_dir"])
        package.mkdir(parents=True, exist_ok=True)
        scene_path = package / "maps" / "JPN-01.mp4"
        with patch(
            "geofactory.media.map_animation_engine.load_natural_earth",
            return_value=(FIXTURE_DATA, FIXTURE_MANIFEST),
        ):
            scene = create_map_scene(
                self.root, scene_path, MapSceneSpec("JPN", duration_seconds=2),
                width=320, height=180, fps=1,
            )
            generate_thumbnail_concepts(
                job["topic"], "JPN", package, self.root,
                headline="TOKYO GEOGRAPHY",
            )
        (package / "map_scenes.json").write_text(
            json.dumps({"scenes": [{
                "path": "maps/JPN-01.mp4",
                "dataset_name": scene["dataset_name"],
                "dataset_version": scene["dataset_version"],
                "licence": scene["licence"],
            }]}),
            encoding="utf-8",
        )
        (package / "attribution.md").write_text(
            "Made with Natural Earth 1:110m Admin 0 Countries 5.1.1 (Public Domain)\n",
            encoding="utf-8",
        )
        (package / "script.md").write_text("# Draft\n", encoding="utf-8")
        (package / "metadata.json").write_text(
            json.dumps({"title": "Tokyo", "description": "Draft"}),
            encoding="utf-8",
        )
        (package / "source_ledger.json").write_text(
            json.dumps({"sources": [], "claims": []}), encoding="utf-8"
        )
        (package / "asset_ledger.json").write_text(
            json.dumps({"assets": []}), encoding="utf-8"
        )
        config = FactoryConfig(
            root=self.root,
            database_path=self.root / "factory.sqlite3",
            output_dir=self.root / "output",
            minimum_free_disk_gb=0,
            width=320,
            height=180,
        )
        report = run_qa(db, job["id"], config)
        codes = {check["code"] for check in report["checks"]}
        self.assertIn("map_scenes_valid", codes)
        self.assertIn("thumbnail_concepts_scored", codes)
        self.assertNotIn("map_attribution_missing", codes)
        self.assertNotIn("thumbnail_scores_invalid", codes)
        self.assertTrue(report["approval_blocked"])


if __name__ == "__main__":
    unittest.main()
