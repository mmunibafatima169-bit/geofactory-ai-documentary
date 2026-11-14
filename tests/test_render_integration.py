"""
FFmpeg Integration Tests with Synthetic Fixtures

Uses FFmpeg lavfi (testsrc, sine) to create tiny synthetic video/audio fixtures
for testing the rendering pipeline end-to-end without external assets.

Note: Some tests require PIL (Pillow) for map_animation_engine. These tests
are conditionally skipped if PIL is not available.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


# Check if FFmpeg tools are available
FFMPEG_AVAILABLE = all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe"))

# Check if PIL is available
try:
    from PIL import Image  # noqa: F401
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Check if media modules (requiring PIL) can be imported
MEDIA_MODULES_AVAILABLE = PIL_AVAILABLE and FFMPEG_AVAILABLE


def _make_synthetic_video(path: Path, duration: float = 2.0, width: int = 320, height: int = 180) -> None:
    """Create a synthetic test video using FFmpeg lavfi."""
    cmd = [
        shutil.which("ffmpeg"), "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={width}x{height}:rate=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create synthetic video: {result.stderr}")


def _make_synthetic_audio(path: Path, duration: float = 2.0, frequency: int = 440) -> None:
    """Create a synthetic test audio using FFmpeg lavfi."""
    cmd = [
        shutil.which("ffmpeg"), "-y", "-v", "error",
        "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=22050",
        "-t", str(duration), "-c:a", "pcm_s16le", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create synthetic audio: {result.stderr}")


def _make_synthetic_narration(path: Path, duration: float = 5.0) -> None:
    """Create a synthetic narration with speech-like pattern."""
    cmd = [
        shutil.which("ffmpeg"), "-y", "-v", "error",
        "-f", "lavfi",
        "-i", f"sine=frequency=220:sample_rate=22050",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:sample_rate=22050",
        "-f", "lavfi",
        "-i", f"sine=frequency=880:sample_rate=22050",
        "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3:duration=first,volume=0.3",
        "-t", str(duration), "-c:a", "pcm_s16le", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create synthetic narration: {result.stderr}")


def _make_srt_file(path: Path, segments: list[tuple[float, float, str]]) -> None:
    """Create an SRT subtitle file from segments (start_s, end_s, text)."""
    lines = []
    for i, (start_s, end_s, text) in enumerate(segments, 1):
        def fmt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        lines.append(f"{i}\n{fmt(start_s)} --> {fmt(end_s)}\n{text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def _probe_video_with_ffprobe(path: Path) -> dict:
    """Probe video file with ffprobe directly (no GeoFactory config needed)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe not found")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"FFprobe failed: {result.stderr[-1000:]}")
    import json as json_mod
    parsed = json_mod.loads(result.stdout)
    if not isinstance(parsed, dict) or not parsed.get("streams"):
        raise RuntimeError("FFprobe found no media streams.")
    return parsed


class FFmpegSyntheticFixturesTests(unittest.TestCase):
    """Test synthetic fixture creation with FFmpeg lavfi (no PIL required)."""
    
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @unittest.skipUnless(FFMPEG_AVAILABLE, "FFmpeg/FFprobe required")
    def test_create_synthetic_video(self) -> None:
        """Test creating synthetic video with testsrc."""
        video = self.root / "test.mp4"
        _make_synthetic_video(video, duration=1.5, width=320, height=180)
        
        self.assertTrue(video.is_file())
        self.assertGreater(video.stat().st_size, 0)
        
        probed = _probe_video_with_ffprobe(video)
        streams = probed["streams"]
        video_stream = next(s for s in streams if s["codec_type"] == "video")
        self.assertEqual((video_stream["width"], video_stream["height"]), (320, 180))
        self.assertEqual(video_stream["codec_name"], "h264")
        
        # Check duration
        format_info = probed.get("format", {})
        duration = float(format_info.get("duration", 0))
        self.assertAlmostEqual(duration, 1.5, delta=0.1)

    @unittest.skipUnless(FFMPEG_AVAILABLE, "FFmpeg/FFprobe required")
    def test_create_synthetic_audio(self) -> None:
        """Test creating synthetic audio with sine wave."""
        audio = self.root / "test.wav"
        _make_synthetic_audio(audio, duration=2.0, frequency=440)
        
        self.assertTrue(audio.is_file())
        self.assertGreater(audio.stat().st_size, 0)
        
        probed = _probe_video_with_ffprobe(audio)
        streams = probed["streams"]
        audio_stream = next(s for s in streams if s["codec_type"] == "audio")
        self.assertEqual(audio_stream["codec_name"], "pcm_s16le")
        self.assertEqual(audio_stream["sample_rate"], "22050")

    @unittest.skipUnless(FFMPEG_AVAILABLE, "FFmpeg/FFprobe required")
    def test_create_synthetic_narration(self) -> None:
        """Test creating synthetic narration with mixed sine waves."""
        narration = self.root / "narration.wav"
        _make_synthetic_narration(narration, duration=3.0)
        
        self.assertTrue(narration.is_file())
        self.assertGreater(narration.stat().st_size, 0)
        
        probed = _probe_video_with_ffprobe(narration)
        format_info = probed.get("format", {})
        duration = float(format_info.get("duration", 0))
        self.assertAlmostEqual(duration, 3.0, delta=0.2)

    @unittest.skipUnless(FFMPEG_AVAILABLE, "FFmpeg/FFprobe required")
    def test_create_srt_file(self) -> None:
        """Test creating SRT subtitle file."""
        srt = self.root / "test.srt"
        _make_srt_file(srt, [
            (0.0, 1.5, "First subtitle"),
            (1.5, 3.0, "Second subtitle"),
        ])
        
        self.assertTrue(srt.is_file())
        content = srt.read_text(encoding="utf-8")
        self.assertIn("00:00:00,000 --> 00:00:01,500", content)
        self.assertIn("First subtitle", content)
        self.assertIn("00:00:01,500 --> 00:00:03,000", content)
        self.assertIn("Second subtitle", content)


@unittest.skipUnless(MEDIA_MODULES_AVAILABLE, "Requires PIL and FFmpeg/FFprobe")
class VideoEditorIntegrationTests(unittest.TestCase):
    """Test the video_editor.py render_video function with synthetic fixtures."""
    
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        
        # Import here to avoid module-level import errors
        from geofactory.core.config import FactoryConfig
        from geofactory.core.database import Database
        from geofactory.core.jobs import create_job
        from geofactory.media.asset_manager import register_asset
        from geofactory.media.video_editor import RenderError, probe_video, render_video
        
        self.FactoryConfig = FactoryConfig
        self.Database = Database
        self.create_job = create_job
        self.register_asset = register_asset
        self.RenderError = RenderError
        self.probe_video = probe_video
        self.render_video = render_video
        
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

    def test_render_video_with_synthetic_image_and_narration(self) -> None:
        """Test basic video render with synthetic image, narration, and SRT."""
        job = self.create_job(
            self.database, "Synthetic render test", "Can we render with lavfi fixtures?",
            self.config.output_dir,
        )
        package = Path(job["output_dir"])
        package.mkdir(parents=True, exist_ok=True)
        
        # Create synthetic image (PNG)
        image = self.root / "test_image.png"
        cmd = [
            shutil.which("ffmpeg"), "-y", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x180:rate=1",
            "-vframes", "1", str(image),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        
        # Register asset
        asset_id = self.register_asset(
            self.database, job["id"], image, "https://example.invalid/synthetic-image",
            "Synthetic test image", "CC0-1.0", "Synthetic fixture, CC0-1.0", True,
        )
        with self.database.connect() as conn:
            asset = dict(conn.execute(
                "SELECT * FROM assets WHERE id = ?", (asset_id,)
            ).fetchone())
        
        # Create synthetic narration and SRT
        narration = package / "narration.wav"
        _make_synthetic_narration(narration, duration=3.0)
        
        subtitles = package / "subtitles.srt"
        _make_srt_file(subtitles, [
            (0.0, 1.5, "This is a synthetic test."),
            (1.5, 3.0, "Checking the render pipeline."),
        ])
        
        # Render
        result = self.render_video(
            self.config, [image], narration, package / "final.mp4", [asset], subtitles,
        )
        
        # Verify output
        self.assertTrue(result.is_file())
        self.assertGreater(result.stat().st_size, 0)
        
        # Probe and verify streams
        probed = self.probe_video(self.config, result)
        streams = probed["streams"]
        kinds = {stream["codec_type"] for stream in streams}
        self.assertTrue({"video", "audio", "subtitle"}.issubset(kinds))
        
        video_stream = next(s for s in streams if s["codec_type"] == "video")
        self.assertEqual((video_stream["width"], video_stream["height"]), (320, 180))
        
        # Verify duration matches narration
        format_info = probed.get("format", {})
        duration = float(format_info.get("duration", 0))
        self.assertGreater(duration, 2.5)
        self.assertLess(duration, 4.0)

    def test_render_video_with_synthetic_video_clip(self) -> None:
        """Test video render with synthetic video clip (not still image)."""
        job = self.create_job(
            self.database, "Synthetic video clip test", "Does video clip priority work?",
            self.config.output_dir,
        )
        package = Path(job["output_dir"])
        package.mkdir(parents=True, exist_ok=True)
        
        # Create synthetic video clip
        video = self.root / "stock.mp4"
        _make_synthetic_video(video, duration=2.0)
        
        # Register as video asset
        with self.database.connect() as conn:
            conn.execute(
                """INSERT INTO assets
                   (id, job_id, title, publisher, path, origin_url, creator, licence,
                    licence_url, attribution, commercial_use, file_sha256, retrieved_at,
                    media_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'video')""",
                (
                    "stock-video", job["id"], "Synthetic stock clip", "Test",
                    str(video), "https://example.invalid/synthetic-video",
                    "Synthetic fixture", "Test License",
                    "https://example.invalid/license",
                    "Synthetic fixture, Test License",
                    hashlib.sha256(video.read_bytes()).hexdigest(), "2026-01-01T00:00:00Z",
                ),
            )
        
        # Also add a fallback still image
        image = self.root / "fallback.png"
        cmd = [
            shutil.which("ffmpeg"), "-y", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x180:rate=1",
            "-vframes", "1", str(image),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        self.register_asset(
            self.database, job["id"], image, "https://example.invalid/fallback",
            "Synthetic fallback", "CC0-1.0", "Synthetic fallback, CC0-1.0", True,
        )
        with self.database.connect() as conn:
            records = [dict(row) for row in conn.execute(
                "SELECT * FROM assets WHERE job_id = ?", (job["id"],)
            )]
        
        narration = package / "narration.wav"
        _make_synthetic_narration(narration, duration=3.0)
        
        subtitles = package / "subtitles.srt"
        _make_srt_file(subtitles, [(0.0, 3.0, "Video clip test.")])
        
        # Should fail without fallback image (video clip too short)
        with self.assertRaisesRegex(self.RenderError, "do not cover the narration"):
            self.render_video(
                self.config, [video], narration, package / "uncovered.mp4",
                records, subtitles,
            )
        
        # Should succeed with fallback image
        result = self.render_video(
            self.config, [image, video], narration, package / "final.mp4",
            records, subtitles,
        )
        
        self.assertTrue(result.is_file())
        probed = self.probe_video(self.config, result)
        kinds = {s["codec_type"] for s in probed["streams"]}
        self.assertTrue({"video", "audio", "subtitle"}.issubset(kinds))


@unittest.skipUnless(MEDIA_MODULES_AVAILABLE, "Requires PIL and FFmpeg/FFprobe")
class DocumentaryRendererIntegrationTests(unittest.TestCase):
    """Test the documentary_renderer.py with synthetic fixtures."""
    
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        
        from geofactory.core.config import FactoryConfig
        from geofactory.core.database import Database
        from geofactory.core.jobs import create_job
        from geofactory.media.asset_manager import register_asset
        from geofactory.media.documentary_renderer import (
            DocumentaryRenderError,
            render_documentary_from_plan,
        )
        
        self.FactoryConfig = FactoryConfig
        self.Database = Database
        self.create_job = create_job
        self.register_asset = register_asset
        self.DocumentaryRenderError = DocumentaryRenderError
        self.render_documentary_from_plan = render_documentary_from_plan
        
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
    
    def _create_documentary_package(self, job_id: str, num_scenes: int = 3) -> tuple[Path, list]:
        """Create a complete documentary package with synthetic assets."""
        package = self.config.output_dir / job_id
        package.mkdir(parents=True, exist_ok=True)
        
        # Create scene manifest
        scenes = []
        cursor = 0.0
        for i in range(num_scenes):
            dur = 5.0
            scenes.append({
                "scene_id": f"scene_{i}",
                "start_s": cursor,
                "end_s": cursor + dur,
                "visual_objective": ["cold_open", "map_context", "photo_evidence"][i % 3],
                "narration": f"Scene {i} narration text for the documentary.",
            })
            cursor += dur
        
        manifest = {
            "title": "Test Documentary",
            "target_duration_s": cursor,
            "scenes": scenes,
        }
        (package / "scene_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        
        # Create asset allocations
        allocations = {"allocations": {}}
        (package / "asset_allocations.json").write_text(json.dumps(allocations), encoding="utf-8")
        
        # Create synthetic assets and register in DB
        db_records = []
        for i in range(num_scenes):
            img = self.root / f"scene_{i}.png"
            cmd = [
                shutil.which("ffmpeg"), "-y", "-v", "error",
                "-f", "lavfi", "-i", f"testsrc=duration=1:size=320x180:rate=1",
                "-vframes", "1", str(img),
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            
            asset_id = self.register_asset(
                self.database, job_id, img, f"https://example.invalid/scene_{i}",
                f"Synthetic scene {i}", "CC0-1.0", f"Synthetic scene {i}, CC0-1.0", True,
            )
            with self.database.connect() as conn:
                asset = dict(conn.execute(
                    "SELECT * FROM assets WHERE id = ?", (asset_id,)
                ).fetchone())
            db_records.append(asset)
            
            # Add to allocations
            allocations["allocations"][f"scene_{i}"] = [{
                "local_path": str(img),
                "asset_id": asset_id,
            }]
        
        (package / "asset_allocations.json").write_text(json.dumps(allocations), encoding="utf-8")
        
        # Create synthetic narration (total duration matches manifest)
        narration = package / "narration.wav"
        _make_synthetic_narration(narration, duration=cursor)
        
        # Create SRT
        subtitles = package / "subtitles.srt"
        srt_segments = []
        for i, scene in enumerate(scenes):
            srt_segments.append((scene["start_s"], scene["end_s"], scene["narration"]))
        _make_srt_file(subtitles, srt_segments)
        
        return package, db_records
    
    def test_render_documentary_from_plan_basic(self) -> None:
        """Test basic documentary rendering from plan with synthetic assets."""
        job = self.create_job(
            self.database, "Documentary render test", "Full pipeline render",
            self.config.output_dir,
        )
        package, db_records = self._create_documentary_package(job["id"], num_scenes=3)
        
        destination = self.root / "documentary.mp4"
        result = self.render_documentary_from_plan(
            self.config, job["id"], package, destination,
        )
        
        # Verify output
        self.assertTrue(result.is_file())
        self.assertGreater(result.stat().st_size, 0)
        
        from geofactory.media.video_editor import probe_video
        probed = probe_video(self.config, result)
        kinds = {s["codec_type"] for s in probed["streams"]}
        self.assertTrue({"video", "audio", "subtitle"}.issubset(kinds))
        
        video_stream = next(s for s in probed["streams"] if s["codec_type"] == "video")
        self.assertEqual((video_stream["width"], video_stream["height"]), (320, 180))
        
        # Verify duration
        format_info = probed.get("format", {})
        duration = float(format_info.get("duration", 0))
        self.assertAlmostEqual(duration, 15.0, delta=0.5)
    
    def test_render_documentary_missing_narration_fails(self) -> None:
        """Test that missing narration raises error."""
        job = self.create_job(
            self.database, "Missing narration test", "Should fail",
            self.config.output_dir,
        )
        package = self.config.output_dir / job["id"]
        package.mkdir(parents=True, exist_ok=True)
        
        manifest = {"title": "Test", "target_duration_s": 10, "scenes": [
            {"scene_id": "s1", "start_s": 0, "end_s": 5, "visual_objective": "photo_evidence", "narration": "Test"}
        ]}
        (package / "scene_manifest.json").write_text(json.dumps(manifest))
        (package / "asset_allocations.json").write_text(json.dumps({"allocations": {}}))
        
        destination = self.root / "fail.mp4"
        with self.assertRaises(self.DocumentaryRenderError) as cm:
            self.render_documentary_from_plan(self.config, job["id"], package, destination)
        self.assertIn("Narration not found", str(cm.exception))
    
    def test_render_documentary_missing_plan_fails(self) -> None:
        """Test that missing plan files raise error."""
        job = self.create_job(
            self.database, "Missing plan test", "Should fail",
            self.config.output_dir,
        )
        package = self.config.output_dir / job["id"]
        package.mkdir(parents=True, exist_ok=True)
        
        destination = self.root / "fail.mp4"
        with self.assertRaises(self.DocumentaryRenderError) as cm:
            self.render_documentary_from_plan(self.config, job["id"], package, destination)
        self.assertIn("Scene manifest not found", str(cm.exception))


@unittest.skipUnless(MEDIA_MODULES_AVAILABLE, "Requires PIL and FFmpeg/FFprobe")
class ShortsGeneratorIntegrationTests(unittest.TestCase):
    """Test the shorts_generator.py with synthetic fixtures."""
    
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        
        from geofactory.core.config import FactoryConfig
        from geofactory.core.database import Database
        from geofactory.core.jobs import create_job
        from geofactory.media.asset_manager import register_asset
        from geofactory.media.shorts_generator import (
            ShortsRenderError,
            generate_shorts_from_documentary,
        )
        
        self.FactoryConfig = FactoryConfig
        self.Database = Database
        self.create_job = create_job
        self.register_asset = register_asset
        self.ShortsRenderError = ShortsRenderError
        self.generate_shorts_from_documentary = generate_shorts_from_documentary
        
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
    
    def _create_shorts_package(self, job_id: str, num_scenes: int = 5) -> tuple[Path, list]:
        """Create a documentary package suitable for Shorts generation."""
        package = self.config.output_dir / job_id
        package.mkdir(parents=True, exist_ok=True)
        
        objectives = ["cold_open", "map_context", "photo_evidence", "comparison_montage", "closing_beat"]
        scenes = []
        cursor = 0.0
        for i in range(num_scenes):
            dur = 10.0
            scenes.append({
                "scene_id": f"scene_{i}",
                "start_s": cursor,
                "end_s": cursor + dur,
                "visual_objective": objectives[i % len(objectives)],
                "narration": f"Scene {i} narration for the short documentary segment.",
            })
            cursor += dur
        
        manifest = {
            "title": "Test Documentary for Shorts",
            "target_duration_s": cursor,
            "scenes": scenes,
        }
        (package / "scene_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        
        allocations = {"allocations": {}}
        db_records = []
        
        for i in range(num_scenes):
            img = self.root / f"shorts_scene_{i}.png"
            cmd = [
                shutil.which("ffmpeg"), "-y", "-v", "error",
                "-f", "lavfi", "-i", f"testsrc=duration=1:size=320x180:rate=1",
                "-vframes", "1", str(img),
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            
            asset_id = self.register_asset(
                self.database, job_id, img, f"https://example.invalid/shorts_scene_{i}",
                f"Synthetic shorts scene {i}", "CC0-1.0", f"Synthetic scene {i}, CC0-1.0", True,
            )
            with self.database.connect() as conn:
                asset = dict(conn.execute(
                    "SELECT * FROM assets WHERE id = ?", (asset_id,)
                ).fetchone())
            db_records.append(asset)
            
            allocations["allocations"][f"scene_{i}"] = [{
                "local_path": str(img),
                "asset_id": asset_id,
            }]
        
        (package / "asset_allocations.json").write_text(json.dumps(allocations), encoding="utf-8")
        
        narration = package / "narration.wav"
        _make_synthetic_narration(narration, duration=cursor)
        
        subtitles = package / "subtitles.srt"
        srt_segments = [(s["start_s"], s["end_s"], s["narration"]) for s in scenes]
        _make_srt_file(subtitles, srt_segments)
        
        return package, db_records
    
    def test_generate_shorts_basic(self) -> None:
        """Test basic Shorts generation with synthetic assets."""
        job = self.create_job(
            self.database, "Shorts test", "Generate vertical Short",
            self.config.output_dir,
        )
        package, db_records = self._create_shorts_package(job["id"], num_scenes=5)
        
        destination = self.root / "shorts.mp4"
        result = self.generate_shorts_from_documentary(
            self.config, job["id"], package, destination,
            target_duration=30.0,
            hook_text="Watch this amazing geography fact!",
        )
        
        self.assertTrue(result.is_file())
        self.assertGreater(result.stat().st_size, 0)
        
        from geofactory.media.video_editor import probe_video
        probed = probe_video(self.config, result)
        kinds = {s["codec_type"] for s in probed["streams"]}
        self.assertTrue({"video", "audio", "subtitle"}.issubset(kinds))
        
        video_stream = next(s for s in probed["streams"] if s["codec_type"] == "video")
        self.assertEqual((video_stream["width"], video_stream["height"]), (1080, 1920))
        
        format_info = probed.get("format", {})
        duration = float(format_info.get("duration", 0))
        self.assertGreaterEqual(duration, 15.0)
        self.assertLessEqual(duration, 60.0)
        self.assertAlmostEqual(duration, 30.0, delta=2.0)
        
        # Verify shorts_subtitles.srt was created
        shorts_srt = package / "shorts_subtitles.srt"
        self.assertTrue(shorts_srt.is_file())
        content = shorts_srt.read_text(encoding="utf-8")
        self.assertIn("-->", content)
    
    def test_generate_shorts_duration_bounds(self) -> None:
        """Test that Shorts duration is clamped to 15-60s."""
        job = self.create_job(
            self.database, "Shorts bounds test", "Duration validation",
            self.config.output_dir,
        )
        package, db_records = self._create_shorts_package(job["id"], num_scenes=3)
        
        destination = self.root / "short.mp4"
        with self.assertRaises(self.ShortsRenderError) as cm:
            self.generate_shorts_from_documentary(
                self.config, job["id"], package, destination,
                target_duration=10.0,
            )
        self.assertIn("15.0-60.0s", str(cm.exception))
        
        destination = self.root / "long.mp4"
        with self.assertRaises(self.ShortsRenderError) as cm:
            self.generate_shorts_from_documentary(
                self.config, job["id"], package, destination,
                target_duration=90.0,
            )
        self.assertIn("15.0-60.0s", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
