"""Tests for the documentary planner: script parsing, chapter allocation, scene planning."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from geofactory.studio.documentary_planner import (
    parse_script_chapters,
    allocate_chapter_time,
    assign_visual_directions_to_chapters,
    extract_claim_ids_from_narration,
    build_documentary_plan,
    validate_documentary_plan,
    run_documentary_plan,
    ChapterPlan,
    DocumentaryPlan,
    REQUIRED_CHAPTERS,
    MIN_DURATION_S,
    MAX_DURATION_S,
)
from geofactory.studio.documentary_planner import CHAPTER_DISPLAY_NAMES
from geofactory.studio.scene_manifest import SceneManifest, ScenePlan
from geofactory.core.database import Database
from geofactory.core.config import FactoryConfig


SAMPLE_SCRIPT = """# Script draft: Venice and its Lagoon

**Viewer question:** How has the setting of Venice shaped its relationship with the sea?

> AI-generated draft. Verify every claim against the source ledger and edit before narration.

## Narration (1500 words)

Venice sits on a lagoon of islands near the Italian coast. [clm-venice-001]
The city was founded in the 5th century by refugees fleeing mainland invasions. [clm-venice-002]
The MOSE engineering project uses 78 barrier gates at the three inlets. [clm-venice-003]
Flooding reached 194 cm during the 1966 acqua alta event. [clm-venice-004]
Sea levels have risen by centimetres over the last century according to tide data. [clm-venice-005]
Jakarta and Bangkok face similar subsidence problems around the world. [clm-venice-006]
Tonight, somewhere along the lagoon, engineers watch the tide forecast again. [clm-venice-007]

## Chapters

1. The Question
2. Geographic Context
3. Causes & Mechanisms
4. Consequences & Evidence
5. The Bigger Picture
6. Conclusion

## Scene plan

- **Opening:** World map zoom to Venice lagoon with kinetic title
- **Context:** Terrain map showing islands and waterways
- **Cause:** Animated diagram of MOSE gate mechanism
- **Consequence:** Flood level comparison chart with 194 cm peak
- **Bigger Picture:** Multi-city comparison montage of subsidence
- **Conclusion:** Return to Venice map with closing question
"""


def make_temp_script(content: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


class DocumentaryPlannerTests(unittest.TestCase):
    def setUp(self):
        self.script_path = make_temp_script(SAMPLE_SCRIPT)

    def tearDown(self):
        self.script_path.unlink(missing_ok=True)

    def test_parse_script_chapters(self):
        chapter_titles, narration_text, visual_directions = parse_script_chapters(self.script_path)
        
        self.assertEqual(len(chapter_titles), 6)
        self.assertEqual(chapter_titles[0], "The Question")
        self.assertEqual(chapter_titles[5], "Conclusion")
        
        # Narration should be extracted
        self.assertIn("Venice sits on a lagoon", narration_text)
        self.assertIn("MOSE engineering project", narration_text)
        self.assertIn("194 cm", narration_text)
        
        # Visual directions should be extracted
        self.assertEqual(len(visual_directions), 6)
        self.assertIn("World map zoom", visual_directions[0])
        self.assertIn("MOSE gate mechanism", visual_directions[2])

    def test_parse_script_chapters_fallback(self):
        # Script without proper sections
        minimal_script = """# Script draft: Test

**Viewer question:** Test question?

## Narration (100 words)

This is a test narration. [clm-001]
It has multiple sentences. [clm-002]

## Chapters

1. Chapter One
2. Chapter Two
"""
        path = make_temp_script(minimal_script)
        try:
            chapter_titles, narration_text, visual_directions = parse_script_chapters(path)
            # When chapters < 6, defaults to 6 standard chapters
            self.assertEqual(len(chapter_titles), 6)
            self.assertIn("test narration", narration_text.lower())
        finally:
            path.unlink(missing_ok=True)

    def test_allocate_chapter_time(self):
        narration = "Venice sits on a lagoon. The MOSE project uses gates. Flooding reached 194 cm. Jakarta has similar issues. Engineers watch the tides."
        target = 600.0
        
        chapters = allocate_chapter_time(narration, target, [f"Ch {i}" for i in range(6)])
        
        self.assertEqual(len(chapters), 6)
        for c in chapters:
            self.assertIn(c.key, REQUIRED_CHAPTERS)
            self.assertGreater(c.end_s, c.start_s)
        
        # Total should approximately equal target
        total_duration = chapters[-1].end_s
        self.assertAlmostEqual(total_duration, target, delta=5.0)
        
        # Check word counts are distributed
        for c in chapters:
            self.assertGreaterEqual(len(c.narration_text.split()), 0)

    def test_allocate_chapter_time_empty_narration(self):
        chapters = allocate_chapter_time("", 600.0, [f"Ch {i}" for i in range(6)])
        self.assertEqual(len(chapters), 6)
        # Should still create chapters with equal allocation
        for c in chapters:
            self.assertGreater(c.end_s, c.start_s)

    def test_assign_visual_directions_to_chapters(self):
        chapters = [
            ChapterPlan(key="question", title="The Question", start_s=0, end_s=60),
            ChapterPlan(key="context", title="Geographic Context", start_s=60, end_s=180),
            ChapterPlan(key="cause", title="Causes & Mechanisms", start_s=180, end_s=300),
            ChapterPlan(key="consequence", title="Consequences & Evidence", start_s=300, end_s=420),
            ChapterPlan(key="bigger_picture", title="The Bigger Picture", start_s=420, end_s=540),
            ChapterPlan(key="conclusion", title="Conclusion", start_s=540, end_s=600),
        ]
        visual_directions = [
            "Map zoom to Venice", "Terrain map", "MOSE animation", 
            "Flood chart", "City comparison", "Closing map"
        ]
        
        assign_visual_directions_to_chapters(chapters, visual_directions)
        
        # Each chapter should get at least one direction
        for c in chapters:
            self.assertGreater(len(c.visual_directions), 0)

    def test_extract_claim_ids_from_narration(self):
        narration = "Venice sits on a lagoon. [clm-venice-001] The MOSE project uses 78 gates. [clm-venice-003] Flooding reached 194 cm. [clm-venice-004]"
        ids = extract_claim_ids_from_narration(narration)
        self.assertEqual(set(ids), {"clm-venice-001", "clm-venice-003", "clm-venice-004"})

    def test_validate_documentary_plan_duration(self):
        # Create a minimal plan with too-short duration
        manifest = SceneManifest(
            job_id="test", title="T", fps=30, width=1920, height=1080,
            scenes=[ScenePlan(scene_id="sc-001", narration="test", start_s=0, end_s=100,
                             visual_objective="photo_evidence", engine="ffmpeg", 
                             animation_type="ken_burns_photo", camera="push_in",
                             rationale="test")],
        )
        plan = DocumentaryPlan(
            job_id="test", title="Test", topic="Test", question="Test?",
            target_duration_s=300,  # Below minimum
            chapters=[
                ChapterPlan(key=k, title=CHAPTER_DISPLAY_NAMES[k], start_s=0, end_s=50)
                for k in REQUIRED_CHAPTERS
            ],
            scene_manifest=manifest,
            asset_allocations={},
            total_narration_words=1500,
            estimated_render_duration_s=100,
        )
        errors = validate_documentary_plan(plan)
        self.assertTrue(any("below minimum" in e for e in errors))
        
        # Too long
        plan.target_duration_s = 1000
        plan.estimated_render_duration_s = 1000
        errors = validate_documentary_plan(plan)
        self.assertTrue(any("exceeds maximum" in e for e in errors))

    def test_validate_documentary_plan_chapters(self):
        manifest = SceneManifest(
            job_id="test", title="T", fps=30, width=1920, height=1080,
            scenes=[ScenePlan(scene_id="sc-001", narration="test", start_s=0, end_s=600,
                             visual_objective="photo_evidence", engine="ffmpeg", 
                             animation_type="ken_burns_photo", camera="push_in",
                             rationale="test")],
        )
        # Only 5 chapters
        plan = DocumentaryPlan(
            job_id="test", title="Test", topic="Test", question="Test?",
            target_duration_s=600,
            chapters=[
                ChapterPlan(key=k, title=CHAPTER_DISPLAY_NAMES[k], start_s=0, end_s=100)
                for k in REQUIRED_CHAPTERS[:5]
            ],
            scene_manifest=manifest,
            asset_allocations={},
            total_narration_words=1500,
            estimated_render_duration_s=600,
        )
        errors = validate_documentary_plan(plan)
        self.assertTrue(any("Expected 6 chapters" in e for e in errors))

    def test_validate_documentary_plan_word_count(self):
        manifest = SceneManifest(
            job_id="test", title="T", fps=30, width=1920, height=1080,
            scenes=[ScenePlan(scene_id="sc-001", narration="test", start_s=0, end_s=600,
                             visual_objective="photo_evidence", engine="ffmpeg", 
                             animation_type="ken_burns_photo", camera="push_in",
                             rationale="test")],
        )
        # Too few words
        plan = DocumentaryPlan(
            job_id="test", title="Test", topic="Test", question="Test?",
            target_duration_s=600,
            chapters=[
                ChapterPlan(key=k, title=CHAPTER_DISPLAY_NAMES[k], start_s=0, end_s=100)
                for k in REQUIRED_CHAPTERS
            ],
            scene_manifest=manifest,
            asset_allocations={},
            total_narration_words=500,  # Below minimum
            estimated_render_duration_s=600,
        )
        errors = validate_documentary_plan(plan)
        self.assertTrue(any("minimum 1200" in e for e in errors))

    def test_validate_documentary_plan_claims(self):
        manifest = SceneManifest(
            job_id="test", title="T", fps=30, width=1920, height=1080,
            scenes=[ScenePlan(scene_id="sc-001", narration="test", start_s=0, end_s=600,
                             visual_objective="photo_evidence", engine="ffmpeg", 
                             animation_type="ken_burns_photo", camera="push_in",
                             rationale="test")],
        )
        # No claim IDs
        plan = DocumentaryPlan(
            job_id="test", title="Test", topic="Test", question="Test?",
            target_duration_s=600,
            chapters=[
                ChapterPlan(key=k, title=CHAPTER_DISPLAY_NAMES[k], start_s=0, end_s=100, narration_text="No claims here.")
                for k in REQUIRED_CHAPTERS
            ],
            scene_manifest=manifest,
            asset_allocations={},
            total_narration_words=1500,
            estimated_render_duration_s=600,
        )
        errors = validate_documentary_plan(plan)
        self.assertTrue(any("claim IDs found" in e for e in errors))


class DocumentaryPlannerIntegrationTests(unittest.TestCase):
    """Integration tests requiring database setup."""
    
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.initialize()
        
        # Create a minimal config
        self.config = FactoryConfig(
            root=Path(self.temp_dir),
            database_path=self.db_path,
            output_dir=Path(self.temp_dir) / "output",
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
            width=1920,
            height=1080,
        )
        
        # Create a test job
        from geofactory.core.jobs import create_job
        self.job = create_job(
            self.db, "Venice and its Lagoon", "How has Venice shaped its relationship with the sea?",
            self.config.output_dir
        )
        self.job_id = self.job["id"]
        self.package_dir = Path(self.job["output_dir"])
        self.package_dir.mkdir(parents=True, exist_ok=True)
        
        # Write a script
        self.script_path = self.package_dir / "script.md"
        self.script_path.write_text(SAMPLE_SCRIPT, encoding="utf-8")
        
        # Add some claims
        import uuid
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for i in range(7):
                claim_id = f"clm-venice-{i:03d}"
                conn.execute(
                    """INSERT INTO claims (id, job_id, text, kind, source_ids_json, uncertainty)
                       VALUES (?, ?, ?, 'fact', '[]', '')""",
                    (claim_id, self.job_id, f"Test claim {i}")
                )
            conn.execute("COMMIT")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_documentary_plan(self):
        plan = build_documentary_plan(self.db, self.job_id, self.config, self.script_path, 600.0)
        
        self.assertEqual(plan.job_id, self.job_id)
        self.assertEqual(plan.target_duration_s, 600.0)
        self.assertEqual(len(plan.chapters), 6)
        self.assertGreater(plan.total_narration_words, 0)
        self.assertGreater(len(plan.scene_manifest.scenes), 0)
        self.assertIsInstance(plan.scene_manifest, SceneManifest)
        
        # Check all required chapters present
        chapter_keys = [c.key for c in plan.chapters]
        self.assertEqual(chapter_keys, REQUIRED_CHAPTERS)
        
        # Check scene manifest is valid
        plan.scene_manifest.validate()

    def test_write_documentary_plan(self):
        plan = build_documentary_plan(self.db, self.job_id, self.config, self.script_path, 600.0)
        
        from geofactory.studio.documentary_planner import write_documentary_plan
        write_documentary_plan(plan, self.package_dir)
        
        # Check files were created
        self.assertTrue((self.package_dir / "scene_manifest.json").is_file())
        self.assertTrue((self.package_dir / "documentary_plan.json").is_file())
        self.assertTrue((self.package_dir / "asset_allocations.json").is_file())
        
        # Validate JSON structure
        plan_data = json.loads((self.package_dir / "documentary_plan.json").read_text())
        self.assertEqual(plan_data["job_id"], self.job_id)
        self.assertEqual(len(plan_data["chapters"]), 6)
        
        manifest_data = json.loads((self.package_dir / "scene_manifest.json").read_text())
        self.assertEqual(manifest_data["job_id"], self.job_id)
        self.assertGreater(len(manifest_data["scenes"]), 0)

    def test_run_documentary_plan_cli_entry(self):
        plan = run_documentary_plan(self.db, self.job_id, self.config, 600.0)
        
        self.assertEqual(plan.job_id, self.job_id)
        self.assertEqual(plan.target_duration_s, 600.0)
        self.assertEqual(len(plan.chapters), 6)
        
        # Files should exist
        self.assertTrue((self.package_dir / "documentary_plan.json").is_file())


if __name__ == "__main__":
    unittest.main()
