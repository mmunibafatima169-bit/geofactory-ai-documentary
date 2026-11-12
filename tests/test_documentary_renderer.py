"""Tests for the documentary renderer: plan consumption and FFmpeg integration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Try to import the renderer - skip tests if PIL not available (test env limitation)
try:
    from geofactory.media.documentary_renderer import (
        load_documentary_plan,
        render_documentary,
        render_documentary_from_plan,
        _package_map_scenes,
    )
    from geofactory.core.config import FactoryConfig
    from geofactory.core.database import Database
    from geofactory.core.jobs import create_job
    from geofactory.studio.scene_manifest import SceneManifest, ScenePlan
    RENDERER_AVAILABLE = True
except ImportError as e:
    if "PIL" in str(e) or "Image" in str(e):
        RENDERER_AVAILABLE = False
    else:
        raise


SAMPLE_MANIFEST = {
    "job_id": "test-job",
    "title": "Test Documentary",
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "scenes": [
        {
            "scene_id": "sc-001",
            "narration": "Venice sits on a lagoon.",
            "start_s": 0.0,
            "end_s": 15.0,
            "visual_objective": "map_context",
            "engine": "remotion",
            "animation_type": "map_highlight",
            "camera": "push_in",
            "text_overlays": ["location_label"],
            "transition": "zoom_punch",
            "sound_fx": ["sting_title"],
            "source_ids": ["clm-001"],
            "rationale": "Opening map zoom"
        },
        {
            "scene_id": "sc-002",
            "narration": "The MOSE project uses 78 gates.",
            "start_s": 15.0,
            "end_s": 35.0,
            "visual_objective": "engineering_demo",
            "engine": "blender",
            "animation_type": "exploded_view",
            "camera": "dolly_orbit",
            "text_overlays": ["part_callouts"],
            "transition": "cut",
            "sound_fx": [],
            "source_ids": ["clm-002"],
            "rationale": "Engineering mechanism"
        },
        {
            "scene_id": "sc-003",
            "narration": "Flooding reached 194 cm in 1966.",
            "start_s": 35.0,
            "end_s": 55.0,
            "visual_objective": "archival_footage",
            "engine": "ffmpeg",
            "animation_type": "licensed_archival_clip",
            "camera": "push_in",
            "text_overlays": [],
            "transition": "cut",
            "sound_fx": [],
            "source_ids": ["clm-003"],
            "rationale": "Historical flood event"
        },
    ],
    "version": 1
}

SAMPLE_ALLOCATIONS = {
    "job_id": "test-job",
    "allocations": {
        "sc-001": [
            {
                "asset_id": "asset-001",
                "title": "Venice Lagoon Map",
                "description": "Satellite view of Venice lagoon",
                "media_type": "image",
                "source_page": "https://commons.wikimedia.org/wiki/File:Venice_lagoon.jpg",
                "download_url": "https://commons.wikimedia.org/wiki/File:Venice_lagoon.jpg",
                "creator": "NASA",
                "licence": "Public domain",
                "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "accessed_at": "2024-01-01",
                "local_path": "/tmp/asset-001.jpg",
                "width": 1920,
                "height": 1080,
                "duration_s": 0.0,
                "sha256": "abc123",
                "tags": ["venice", "lagoon", "map"]
            }
        ],
        "sc-002": [
            {
                "asset_id": "asset-002",
                "title": "MOSE Gate Animation",
                "description": "3D animation of MOSE gate",
                "media_type": "video",
                "source_page": "https://example.com/mose",
                "download_url": "https://example.com/mose.mp4",
                "creator": "Engineering Corp",
                "licence": "CC BY 4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                "accessed_at": "2024-01-01",
                "local_path": "/tmp/asset-002.mp4",
                "width": 1920,
                "height": 1080,
                "duration_s": 20.0,
                "sha256": "def456",
                "tags": ["mose", "engineering", "gate"]
            }
        ],
        "sc-003": []
    }
}


@unittest.skipIf(not RENDERER_AVAILABLE, "PIL not available in test environment")
class DocumentaryRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.package_dir = Path(self.temp_dir)
        
        # Write sample manifest and allocations
        (self.package_dir / "scene_manifest.json").write_text(
            json.dumps(SAMPLE_MANIFEST, indent=2), encoding="utf-8"
        )
        (self.package_dir / "asset_allocations.json").write_text(
            json.dumps(SAMPLE_ALLOCATIONS, indent=2), encoding="utf-8"
        )
        
        # Create dummy narration and subtitle files
        (self.package_dir / "narration.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
        (self.package_dir / "subtitles.srt").write_text(
            "1\n00:00:00,000 --> 00:00:05,000\nTest\n", encoding="utf-8"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_documentary_plan(self):
        manifest, allocations = load_documentary_plan(self.package_dir)
        
        self.assertEqual(manifest["job_id"], "test-job")
        self.assertEqual(len(manifest["scenes"]), 3)
        self.assertEqual(allocations["job_id"], "test-job")
        self.assertIn("sc-001", allocations["allocations"])
        self.assertIn("sc-002", allocations["allocations"])
        self.assertIn("sc-003", allocations["allocations"])

    def test_load_documentary_plan_missing_files(self):
        # Remove manifest
        (self.package_dir / "scene_manifest.json").unlink()
        
        with self.assertRaises(Exception) as ctx:
            load_documentary_plan(self.package_dir)
        self.assertIn("Scene manifest not found", str(ctx.exception))

    def test_package_map_scenes_empty(self):
        scenes = _package_map_scenes(self.package_dir)
        self.assertEqual(scenes, [])

    def test_package_map_scenes_with_maps(self):
        maps_dir = self.package_dir / "maps"
        maps_dir.mkdir()
        map_file = maps_dir / "ITA-01.mp4"
        map_file.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
        
        with patch('geofactory.media.documentary_renderer.validate_map_scene') as mock_validate:
            mock_validate.return_value = {"scene": {"country_iso_a3": "ITA"}}
            scenes = _package_map_scenes(self.package_dir)
            self.assertEqual(len(scenes), 1)
            self.assertEqual(scenes[0], map_file)


@unittest.skipIf(not RENDERER_AVAILABLE, "PIL not available in test environment")
class DocumentaryRendererIntegrationTests(unittest.TestCase):
    """Integration tests with mocked FFmpeg."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.initialize()
        
        self.config = FactoryConfig(
            root=Path(self.temp_dir),
            database_path=self.db_path,
            output_dir=Path(self.temp_dir) / "output",
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
            width=1920,
            height=1080,
            minimum_free_disk_gb=1.0,
        )
        
        self.job = create_job(
            self.db, "Test Topic", "Test question?",
            self.config.output_dir
        )
        self.job_id = self.job["id"]
        self.package_dir = Path(self.job["output_dir"])
        self.package_dir.mkdir(parents=True, exist_ok=True)
        
        # Write plan files
        (self.package_dir / "scene_manifest.json").write_text(
            json.dumps(SAMPLE_MANIFEST, indent=2), encoding="utf-8"
        )
        (self.package_dir / "asset_allocations.json").write_text(
            json.dumps(SAMPLE_ALLOCATIONS, indent=2), encoding="utf-8"
        )
        
        # Create dummy narration and subtitle files
        (self.package_dir / "narration.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
        (self.package_dir / "subtitles.srt").write_text(
            "1\n00:00:00,000 --> 00:00:05,000\nTest\n", encoding="utf-8"
        )
        
        # Add assets to database
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO assets (id, job_id, title, path, origin_url, creator, licence, 
                       licence_url, attribution, commercial_use, file_sha256, media_type, retrieved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("asset-001", self.job_id, "Venice Map", "/tmp/asset-001.jpg",
                 "https://commons.wikimedia.org/wiki/File:Venice_lagoon.jpg",
                 "NASA", "Public domain", "https://creativecommons.org/publicdomain/zero/1.0/",
                 "NASA", 1, "abc123", "image", "2024-01-01")
            )
            conn.execute(
                """INSERT INTO assets (id, job_id, title, path, origin_url, creator, licence, 
                       licence_url, attribution, commercial_use, file_sha256, media_type, retrieved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("asset-002", self.job_id, "MOSE Animation", "/tmp/asset-002.mp4",
                 "https://example.com/mose", "Engineering Corp", "CC BY 4.0",
                 "https://creativecommons.org/licenses/by/4.0/",
                 "Engineering Corp", 1, "def456", "video", "2024-01-01")
            )
            conn.execute("COMMIT")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('geofactory.media.documentary_renderer.shutil.which')
    @patch('geofactory.media.documentary_renderer.subprocess.run')
    @patch('geofactory.media.documentary_renderer.shutil.disk_usage')
    @patch('geofactory.media.documentary_renderer.audio_duration_seconds')
    def test_render_documentary_from_plan_missing_plan(self, mock_duration, mock_disk, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/ffmpeg"
        mock_disk.return_value = MagicMock(free=10 * 1024**3)
        mock_duration.return_value = 60.0
        
        # Remove plan files
        (self.package_dir / "scene_manifest.json").unlink()
        
        with self.assertRaises(Exception) as ctx:
            render_documentary_from_plan(self.config, self.job_id, self.package_dir, self.package_dir / "final.mp4")
        self.assertIn("Documentary plan not complete", str(ctx.exception))

    @patch('geofactory.media.documentary_renderer.shutil.which')
    @patch('geofactory.media.documentary_renderer.subprocess.run')
    @patch('geofactory.media.documentary_renderer.shutil.disk_usage')
    @patch('geofactory.media.documentary_renderer.audio_duration_seconds')
    @patch('geofactory.media.documentary_renderer.sha256_file')
    @patch('geofactory.media.documentary_renderer.probe_video')
    def test_render_documentary_from_plan_missing_narration(self, mock_probe, mock_sha256, mock_duration, mock_disk, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/ffmpeg"
        mock_disk.return_value = MagicMock(free=10 * 1024**3)
        mock_duration.return_value = 60.0
        mock_sha256.return_value = "abc123"
        mock_probe.return_value = {"streams": [{"codec_type": "video", "width": 1920, "height": 1080}], "format": {"duration": "20.0"}}
        
        # Remove narration
        (self.package_dir / "narration.wav").unlink()
        
        with self.assertRaises(Exception) as ctx:
            render_documentary_from_plan(self.config, self.job_id, self.package_dir, self.package_dir / "final.mp4")
        self.assertIn("Narration not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
