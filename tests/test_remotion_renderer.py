"""Tests for the Remotion renderer: manifest preparation and CLI integration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Try to import the remotion renderer
try:
    from geofactory.media.remotion_renderer import (
        prepare_scene_manifest_for_remotion,
        render_with_remotion,
        render_documentary_remotion,
        RemotionRendererError,
        RemotionRenderResult,
    )
    from geofactory.core.config import FactoryConfig
    from geofactory.studio.scene_manifest import SceneManifest, ScenePlan
    REMOTION_RENDERER_AVAILABLE = True
except ImportError as e:
    REMOTION_RENDERER_AVAILABLE = False


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


class RemotionRendererManifestTests(unittest.TestCase):
    """Tests for scene manifest preparation for Remotion."""

    def setUp(self):
        if not REMOTION_RENDERER_AVAILABLE:
            self.skipTest("Remotion renderer not importable")
        
        self.temp_dir = tempfile.mkdtemp(prefix="geofactory_test_")
        self.temp_path = Path(self.temp_dir)
        
        # Create a valid SceneManifest
        self.manifest = SceneManifest(
            job_id="test-job",
            title="Test Documentary",
            fps=30,
            width=1920,
            height=1080,
            scenes=[
                ScenePlan(
                    scene_id="sc-001",
                    narration="Venice sits on a lagoon.",
                    start_s=0.0,
                    end_s=15.0,
                    visual_objective="map_context",
                    engine="remotion",
                    animation_type="map_highlight",
                    camera="push_in",
                    text_overlays=["location_label"],
                    transition="zoom_punch",
                    sound_fx=["sting_title"],
                    source_ids=["clm-001"],
                    rationale="Opening map zoom"
                ),
                ScenePlan(
                    scene_id="sc-002",
                    narration="The MOSE project uses 78 gates.",
                    start_s=15.0,
                    end_s=35.0,
                    visual_objective="engineering_demo",
                    engine="blender",
                    animation_type="exploded_view",
                    camera="dolly_orbit",
                    text_overlays=["part_callouts"],
                    transition="cut",
                    sound_fx=[],
                    source_ids=["clm-002"],
                    rationale="Engineering mechanism"
                ),
            ]
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_prepare_scene_manifest_for_remotion_creates_valid_json(self):
        """Test that manifest preparation creates valid JSON with all required fields."""
        manifest_path = prepare_scene_manifest_for_remotion(self.manifest, self.temp_path)
        
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(manifest_path.name, "scene_manifest.json")
        
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check top-level fields
        self.assertEqual(data["job_id"], "test-job")
        self.assertEqual(data["title"], "Test Documentary")
        self.assertEqual(data["fps"], 30)
        self.assertEqual(data["width"], 1920)
        self.assertEqual(data["height"], 1080)
        
        # Check scenes array
        self.assertEqual(len(data["scenes"]), 2)
        
        # Check first scene fields
        scene1 = data["scenes"][0]
        self.assertEqual(scene1["scene_id"], "sc-001")
        self.assertEqual(scene1["narration"], "Venice sits on a lagoon.")
        self.assertEqual(scene1["start_s"], 0.0)
        self.assertEqual(scene1["end_s"], 15.0)
        self.assertEqual(scene1["visual_objective"], "map_context")
        self.assertEqual(scene1["engine"], "remotion")
        self.assertEqual(scene1["animation_type"], "map_highlight")
        self.assertEqual(scene1["camera"], "push_in")
        self.assertEqual(scene1["text_overlays"], ["location_label"])
        self.assertEqual(scene1["transition"], "zoom_punch")
        self.assertEqual(scene1["sound_fx"], ["sting_title"])
        self.assertEqual(scene1["source_ids"], ["clm-001"])
        self.assertEqual(scene1["rationale"], "Opening map zoom")
        
        # Check second scene fields
        scene2 = data["scenes"][1]
        self.assertEqual(scene2["scene_id"], "sc-002")
        self.assertEqual(scene2["visual_objective"], "engineering_demo")
        self.assertEqual(scene2["engine"], "blender")
        self.assertEqual(scene2["transition"], "cut")

    def test_prepare_scene_manifest_preserves_order(self):
        """Test that scene order is preserved in the output."""
        manifest_path = prepare_scene_manifest_for_remotion(self.manifest, self.temp_path)
        
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        scene_ids = [s["scene_id"] for s in data["scenes"]]
        self.assertEqual(scene_ids, ["sc-001", "sc-002"])


class RemotionRendererCliIntegrationTests(unittest.TestCase):
    """Tests for CLI integration with remotion-render command."""

    def setUp(self):
        if not REMOTION_RENDERER_AVAILABLE:
            self.skipTest("Remotion renderer not importable")
        
        self.temp_dir = tempfile.mkdtemp(prefix="geofactory_test_")
        self.temp_path = Path(self.temp_dir)
        
        # Create package directory with required files
        self.package_dir = self.temp_path / "output" / "test-job"
        self.package_dir.mkdir(parents=True, exist_ok=True)
        
        # Write scene manifest
        manifest_path = self.package_dir / "scene_manifest.json"
        manifest_path.write_text(json.dumps(SAMPLE_MANIFEST, indent=2))
        
        # Create dummy narration and subtitle files
        (self.package_dir / "narration.wav").write_bytes(b"dummy")
        (self.package_dir / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nTest\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("geofactory.media.remotion_renderer._find_remotion_project_root")
    def test_render_with_remotion_fails_when_project_not_found(self, mock_find_root):
        """Test that render_with_remotion fails gracefully when Remotion project not found."""
        mock_find_root.return_value = None
        
        config = FactoryConfig(
            root=self.temp_path,
            database_path=self.temp_path / "test.sqlite3",
            output_dir=self.temp_path / "output",
        )
        
        with self.assertRaises(RemotionRendererError) as cm:
            render_with_remotion(config, "test-job", self.package_dir)
        
        self.assertIn("Remotion project not found", str(cm.exception))

    @patch("geofactory.media.remotion_renderer._find_remotion_project_root")
    @patch("geofactory.media.remotion_renderer._ensure_remotion_deps")
    @patch("geofactory.media.remotion_renderer._ensure_chrome")
    def test_render_with_remotion_fails_when_chrome_not_available(self, mock_chrome, mock_deps, mock_find_root):
        """Test that render_with_remotion fails when Chrome is not available."""
        mock_find_root.return_value = self.temp_path / "studio" / "remotion"
        mock_chrome.return_value = False
        
        config = FactoryConfig(
            root=self.temp_path,
            database_path=self.temp_path / "test.sqlite3",
            output_dir=self.temp_path / "output",
        )
        
        with self.assertRaises(RemotionRendererError) as cm:
            render_with_remotion(config, "test-job", self.package_dir)
        
        self.assertIn("Chrome/Chromium not found", str(cm.exception))

    def test_render_documentary_remotion_validates_manifest(self):
        """Test that render_documentary_remotion validates the manifest before rendering."""
        from geofactory.studio.scene_manifest import ManifestError
        
        # Create manifest with invalid scene (end_s < start_s)
        bad_manifest = {
            "job_id": "test-job",
            "title": "Test",
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "scenes": [
                {
                    "scene_id": "sc-001",
                    "narration": "Test",
                    "start_s": 10.0,
                    "end_s": 5.0,  # Invalid: end before start
                    "visual_objective": "map_context",
                    "engine": "remotion",
                    "animation_type": "map_highlight",
                    "camera": "push_in",
                    "text_overlays": [],
                    "transition": "cut",
                    "sound_fx": [],
                    "source_ids": [],
                    "rationale": "Test"
                }
            ],
        }
        
        bad_manifest_path = self.package_dir / "scene_manifest.json"
        bad_manifest_path.write_text(json.dumps(bad_manifest, indent=2))
        
        config = FactoryConfig(
            root=self.temp_path,
            database_path=self.temp_path / "test.sqlite3",
            output_dir=self.temp_path / "output",
        )
        
        with self.assertRaises(ManifestError):
            render_documentary_remotion(config, "test-job", self.package_dir, self.package_dir / "output.mp4")


class RemotionRendererCompatibilityTests(unittest.TestCase):
    """Tests for compatibility with FFmpeg renderer and existing pipeline."""

    def setUp(self):
        if not REMOTION_RENDERER_AVAILABLE:
            self.skipTest("Remotion renderer not importable")
        
        self.temp_dir = tempfile.mkdtemp(prefix="geofactory_test_")
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scene_manifest_schema_matches_ffmpeg_renderer(self):
        """Test that the SceneManifest schema used by Remotion matches FFmpeg renderer expectations."""
        # Both renderers should accept the same SceneManifest format
        manifest = SceneManifest(
            job_id="test-job",
            title="Test",
            fps=30,
            width=1920,
            height=1080,
            scenes=[
                ScenePlan(
                    scene_id="sc-001",
                    narration="Test scene",
                    start_s=0.0,
                    end_s=10.0,
                    visual_objective="map_context",
                    engine="remotion",
                    animation_type="map_highlight",
                    camera="push_in",
                    text_overlays=["location_label"],
                    transition="zoom_punch",
                    sound_fx=[],
                    source_ids=["clm-001"],
                    rationale="Test"
                )
            ]
        )
        
        # Validate manifest (this tests the schema compatibility)
        manifest.validate()
        
        # Check that all required fields exist
        scene = manifest.scenes[0]
        self.assertIsNotNone(scene.scene_id)
        self.assertIsNotNone(scene.narration)
        self.assertGreater(scene.end_s, scene.start_s)
        self.assertIn(scene.visual_objective, [
            "map_context", "engineering_demo", "data_chart",
            "archival_footage", "cinematic_footage", "comparison_montage",
            "satellite_imagery", "photo_evidence"
        ])
        self.assertIn(scene.engine, ["remotion", "blender", "manim", "ffmpeg"])
        self.assertIn(scene.transition, ["cut", "zoom_punch", "wipe_map", "dip_to_black", "crossfade"])

    def test_prepare_manifest_output_matches_inputprops_expectation(self):
        """Test that the prepared manifest matches what DynamicDocumentary.tsx expects."""
        manifest = SceneManifest(
            job_id="test-job",
            title="Test Documentary",
            fps=30,
            width=1920,
            height=1080,
            scenes=[
                ScenePlan(
                    scene_id="sc-001",
                    narration="Test narration",
                    start_s=0.0,
                    end_s=15.0,
                    visual_objective="map_context",
                    engine="remotion",
                    animation_type="map_highlight",
                    camera="push_in",
                    text_overlays=["location_label"],
                    transition="zoom_punch",
                    sound_fx=["sting_title"],
                    source_ids=["clm-001"],
                    rationale="Test"
                )
            ]
        )
        
        manifest_path = prepare_scene_manifest_for_remotion(manifest, self.temp_path)
        
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check structure matches DynamicDocumentaryProps interface
        self.assertIn("job_id", data)
        self.assertIn("title", data)
        self.assertIn("fps", data)
        self.assertIn("width", data)
        self.assertIn("height", data)
        self.assertIn("scenes", data)
        
        # Check scene structure matches ScenePlan interface in TypeScript
        scene = data["scenes"][0]
        required_fields = [
            "scene_id", "narration", "start_s", "end_s",
            "visual_objective", "engine", "animation_type", "camera",
            "text_overlays", "transition", "sound_fx", "source_ids", "rationale"
        ]
        for field in required_fields:
            self.assertIn(field, scene, f"Missing required field: {field}")


if __name__ == "__main__":
    unittest.main()
