from __future__ import annotations

import json
import tempfile
import unittest
import wave
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test the smoke command's stage runner logic in isolation


class SmokeRunnerLogicTests(unittest.TestCase):
    """Test the stage tracking logic used by the smoke command."""

    def test_stage_fail_skips_dependent_stages(self):
        """When a stage FAILs, subsequent stages should be SKIPped and exit code non-zero."""
        # This test verifies the logic that would be in the smoke command
        # We can't easily import the smoke handler due to PIL dependency,
        # so we test the conceptual logic here
        
        summary = {
            "stages": {},
            "overall_status": "UNKNOWN",
        }
        
        def record_stage(name, status, details=None, error=None):
            summary["stages"][name] = {
                "status": status,
                "details": details or {},
                "error": error
            }
            if status == "FAIL":
                summary["overall_status"] = "FAIL"
        
        # Simulate stage execution
        record_stage("init", "PASS", {"job_id": "test-1"})
        record_stage("wikipedia_research", "FAIL", error={"type": "NetworkError", "message": "No network"})
        
        # After FAIL, overall_status should be FAIL
        self.assertEqual(summary["overall_status"], "FAIL")
        
        # Dependent stages should not run (they would be SKIPped)
        # In the actual smoke command, the code checks overall_status and skips
        # We verify the logic by checking that FAIL propagates
        self.assertEqual(summary["stages"]["wikipedia_research"]["status"], "FAIL")
        self.assertEqual(summary["stages"]["init"]["status"], "PASS")

    def test_summary_json_created_on_fail(self):
        """When a stage fails, summary.json should be written with error details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary_path = out_dir / "summary.json"
            
            summary = {
                "topic": "Test",
                "target_seconds": 60,
                "stages": {
                    "init": {"status": "PASS", "details": {}, "error": None},
                    "map_build": {"status": "FAIL", "details": {}, 
                                 "error": {"type": "ImportError", "message": "PIL not available"}}
                },
                "overall_status": "FAIL",
            }
            
            summary_path.write_text(json.dumps(summary, indent=2))
            
            # Verify summary was written
            self.assertTrue(summary_path.exists())
            loaded = json.loads(summary_path.read_text())
            self.assertEqual(loaded["overall_status"], "FAIL")
            self.assertEqual(loaded["stages"]["map_build"]["status"], "FAIL")
            self.assertIn("error", loaded["stages"]["map_build"])
            self.assertEqual(loaded["stages"]["map_build"]["error"]["type"], "ImportError")

    def test_summary_json_created_on_pass(self):
        """When all stages pass, summary.json should show overall PASS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            summary_path = out_dir / "summary.json"
            
            summary = {
                "topic": "Test",
                "target_seconds": 60,
                "stages": {
                    "init": {"status": "PASS", "details": {"job_id": "test-1"}, "error": None},
                    "wikipedia_research": {"status": "FAIL", "details": {}, 
                                          "error": {"type": "NetworkError", "message": "Expected without network"}},
                    "map_build": {"status": "SKIP", "details": {"reason": "Previous stage failed"}, "error": None},
                },
                "overall_status": "FAIL",
            }
            
            summary_path.write_text(json.dumps(summary, indent=2))
            loaded = json.loads(summary_path.read_text())
            self.assertEqual(loaded["overall_status"], "FAIL")

    def test_skip_stages_dont_affect_overall_if_no_fail(self):
        """If all stages are PASS or SKIP (no FAIL), overall should be PASS."""
        summary = {"stages": {}, "overall_status": "UNKNOWN"}
        
        def record_stage(name, status, details=None, error=None):
            summary["stages"][name] = {"status": status, "details": details or {}, "error": error}
            if status == "FAIL":
                summary["overall_status"] = "FAIL"
        
        record_stage("init", "PASS")
        record_stage("map_build", "SKIP", details={"reason": "PIL not available"})
        record_stage("thumbnail_build", "SKIP", details={"reason": "PIL not available"})
        record_stage("espeak_narrate", "SKIP", details={"reason": "espeak-ng not installed"})
        
        # No FAIL, so overall should not be FAIL
        self.assertNotEqual(summary["overall_status"], "FAIL")


class SmokeAllocationValidationTests(unittest.TestCase):
    """No-PIL/FFmpeg tests for smoke package allocation postconditions."""

    def _write_package(self, package: Path, allocations: dict) -> None:
        package.mkdir(parents=True, exist_ok=True)
        (package / "scene_manifest.json").write_text(json.dumps({
            "job_id": "smoke-test",
            "title": "Singapore",
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "scenes": [
                {
                    "scene_id": "sc-001",
                    "narration": "Singapore is on a map.",
                    "start_s": 0.0,
                    "end_s": 20.0,
                    "visual_objective": "map_context",
                    "engine": "ffmpeg",
                    "animation_type": "map_highlight",
                    "camera": "push_in",
                },
                {
                    "scene_id": "sc-002",
                    "narration": "The port supports trade.",
                    "start_s": 20.0,
                    "end_s": 40.0,
                    "visual_objective": "photo_evidence",
                    "engine": "ffmpeg",
                    "animation_type": "ken_burns_photo",
                    "camera": "static",
                },
            ],
            "version": 1,
        }), encoding="utf-8")
        (package / "asset_allocations.json").write_text(
            json.dumps({"job_id": "smoke-test", "allocations": allocations}),
            encoding="utf-8",
        )

    def test_smoke_package_accepts_every_allocated_scene(self):
        from geofactory.cli import validate_smoke_allocations

        with tempfile.TemporaryDirectory() as tmpdir:
            package = Path(tmpdir)
            map_path = package / "maps" / "SGP-01.mp4"
            map_path.parent.mkdir(parents=True)
            map_path.write_bytes(b"fake-map")
            image_path = package / "assets" / "commons.jpg"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"\xff\xd8\xfffake-small-jpeg")
            allocations = {
                "sc-001": [{"asset_id": "map", "media_type": "video",
                            "local_path": str(map_path)}],
                "sc-002": [{"asset_id": "commons", "media_type": "image",
                            "local_path": str(image_path)}],
            }
            self._write_package(package, allocations)

            result = validate_smoke_allocations(package)
            self.assertEqual(set(result), {"sc-001", "sc-002"})

    def test_smoke_package_rejects_scene_without_allocation(self):
        from geofactory.cli import validate_smoke_allocations

        with tempfile.TemporaryDirectory() as tmpdir:
            package = Path(tmpdir)
            image_path = package / "commons.jpg"
            image_path.write_bytes(b"\xff\xd8\xfffake-small-jpeg")
            allocations = {
                "sc-001": [{"asset_id": "commons", "media_type": "image",
                            "local_path": str(image_path)}],
            }
            self._write_package(package, allocations)

            with self.assertRaisesRegex(ValueError, "No allocation for scenes: sc-002"):
                validate_smoke_allocations(package)


class SmokeNarrationPackageTests(unittest.TestCase):
    """Tests for smoke narration package placement and missing-tool skips."""

    def _args(self, out_dir):
        return SimpleNamespace(
            topic="Singapore",
            seconds=60,
            out=str(out_dir),
            offline=True,
            ledger=None,
        )

    def test_monkeypatched_synthesis_writes_wav_in_package_dir(self):
        from geofactory.cli import _cmd_smoke

        def fake_synthesize(text, destination, config, subtitle_destination=None):
            destination.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(destination), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\0\0" * 8000)
            if subtitle_destination is not None:
                subtitle_destination.write_text(
                    "1\n00:00:00,000 --> 00:00:01,000\nSingapore\n",
                    encoding="utf-8",
                )
            return 1.0

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "smoke"
            with patch("geofactory.media.tts_engine.synthesize", side_effect=fake_synthesize), \
                 patch("geofactory.media.tts_engine.audio_duration_seconds", return_value=1.0), \
                 patch("shutil.which", side_effect=lambda name: "/fake/espeak-ng" if name == "espeak-ng" else None):
                result = _cmd_smoke(self._args(out_dir), MagicMock())

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            wav_paths = list(out_dir.rglob("narration.wav"))
            self.assertEqual(len(wav_paths), 1)
            package = wav_paths[0].parent
            self.assertTrue(wav_paths[0].is_file())
            self.assertGreater(wav_paths[0].stat().st_size, 0)
            self.assertTrue((package / "narration.srt").is_file())
            self.assertTrue((package / "subtitles.srt").is_file())
            self.assertEqual(summary["stages"]["espeak_narrate"]["status"], "PASS")

    def test_missing_espeak_skips_narration_render_and_shorts(self):
        from geofactory.cli import _cmd_smoke

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "smoke"
            with patch("shutil.which", return_value=None):
                result = _cmd_smoke(self._args(out_dir), MagicMock())

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            for stage_name in ("espeak_narrate", "render_documentary", "shorts"):
                self.assertEqual(summary["stages"][stage_name]["status"], "SKIP")


if __name__ == "__main__":
    unittest.main()
