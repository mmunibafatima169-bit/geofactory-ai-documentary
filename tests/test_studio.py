"""Tests for the studio layer: manifest schema, Visual Director, editorial QA."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from geofactory.studio.asset_selector import VisualAssetCandidate, score_candidate
from geofactory.studio.editorial_qa import (
    build_report, check_reuses, check_static_walls,
)
from geofactory.studio.factual_verifier import verify_fact_ledger
from geofactory.studio.scene_manifest import ManifestError, SceneManifest, ScenePlan
from geofactory.studio.visual_director import Segment, plan_scenes, rank_visual_treatments


def scene(n: int, start: float, end: float, engine: str = "ffmpeg",
          anim: str = "ken_burns_photo", assets: list[str] | None = None,
          objective: str = "photo_evidence") -> ScenePlan:
    return ScenePlan(
        scene_id=f"sc-{n:03d}", narration=f"Narration beat {n}.",
        start_s=start, end_s=end, visual_objective=objective,
        engine=engine, animation_type=anim, camera="push_in",
        assets=assets or [], rationale="test",
    )


class ManifestTests(unittest.TestCase):
    def test_valid_manifest_round_trips(self) -> None:
        manifest = SceneManifest(
            job_id="job-1", title="T", fps=30, width=1920, height=1080,
            scenes=[scene(1, 0, 12), scene(2, 12, 24), scene(3, 24, 36)],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene_manifest.json"
            manifest.save(path)
            loaded = SceneManifest.load(path)
        self.assertEqual(len(loaded.scenes), 3)
        json.loads(manifest.to_json())

    def test_overlap_or_out_of_order_rejected(self) -> None:
        bad = SceneManifest(job_id="j", title="T", fps=30, width=1920, height=1080,
                            scenes=[scene(1, 6, 18), scene(2, 0, 6)])
        with self.assertRaises(ManifestError):
            bad.validate()

    def test_unknown_engine_rejected(self) -> None:
        with self.assertRaises(ManifestError):
            scene(1, 0, 10, engine="mspaint").validate()

    def test_oversized_scene_needs_splitting(self) -> None:
        with self.assertRaises(ManifestError):
            scene(1, 0, 55.0).validate()


class VisualDirectorTests(unittest.TestCase):
    def test_engine_rules_and_fallbacks(self) -> None:
        # >1.2s silences between beats keep each sentence in its own scene
        segments = [
            Segment("Venice sits on a lagoon of islands near the Italian coast.", 0, 6),
            Segment("The MOSE engineering uses 78 barrier gates at the inlets.", 8, 14),
            Segment("Jakarta and Bangkok face the same problem around the world.", 16, 22),
            Segment("Sea levels rose by measured centimetres in the data.", 24, 30),
        ]
        manifest = plan_scenes("job-9", "Venice", segments,
                               engines_available={"ffmpeg", "remotion", "manim"})
        self.assertEqual(len(manifest.scenes), 4)
        engines = {s.engine for s in manifest.scenes}
        self.assertIn("remotion", engines)   # map + comparison beats
        self.assertIn("manim", engines)      # numeric beats
        map_scene = manifest.scenes[0]
        self.assertEqual(map_scene.visual_objective, "map_context")
        self.assertEqual(map_scene.engine, "remotion")
        eng = manifest.scenes[1]
        self.assertEqual(eng.engine, "manim")            # blender unavailable → fallback
        self.assertIn("fallen back", eng.rationale)
        self.assertTrue(all(s.rationale.strip() for s in manifest.scenes))

    def test_long_beats_split_at_cap(self) -> None:
        segments = [Segment(f"Sentence number {i} carries on. " * 3, i * 8.0, (i + 1) * 8.0)
                    for i in range(8)]
        manifest = plan_scenes("job-8", "T", segments, engines_available={"ffmpeg"})
        self.assertGreater(len(manifest.scenes), 1)
        for s in manifest.scenes:
            self.assertLessEqual(s.end_s - s.start_s, 40.0)


class EditorialQaTests(unittest.TestCase):
    def test_static_wall_and_reuse_flags(self) -> None:
        manifest = SceneManifest(
            job_id="j", title="T", fps=30, width=1920, height=1080,
            scenes=[
                scene(1, 0, 30),                              # still > 22s → static wall
                scene(2, 30, 42, assets=["a.jpg"]),
                scene(3, 42, 54, assets=["a.jpg"]),           # adjacent reuse
                scene(4, 54, 66, assets=["b.jpg"]),
                scene(5, 66, 78, assets=["a.jpg"]),
                scene(6, 78, 90, assets=["a.jpg"]),           # 4 uses → overused
            ],
        )
        repeated, findings = check_reuses(manifest)
        self.assertIn("a.jpg", repeated)
        self.assertTrue(any(f.code == "adjacent_asset_reuse" for f in findings))
        wall, wfindings = check_static_walls(manifest)
        self.assertAlmostEqual(wall, 30.0)
        self.assertTrue(any(f.code == "static_wall" for f in wfindings))
        report = build_report(manifest)
        self.assertGreaterEqual(report.critical_count, 2)
        self.assertIn("limits", report.to_dict())

    def test_clean_manifest_passes_with_note(self) -> None:
        manifest = SceneManifest(
            job_id="j", title="T", fps=30, width=1920, height=1080,
            scenes=[scene(1, 0, 12), scene(2, 14, 26), scene(3, 28, 40)],
        )
        report = build_report(manifest)
        self.assertEqual(report.critical_count, 0)
        self.assertTrue(any(f.code == "editorial_clean" for f in report.findings))


class AssetAndFactTests(unittest.TestCase):
    def test_relevant_licensed_footage_scores_above_generic(self) -> None:
        relevant = VisualAssetCandidate(
            "venice", "Gondolas in Venice", "Canal water and Venice city",
            "video", "https://commons.wikimedia.org/wiki/File:X.webm",
            "https://upload.wikimedia.org/x.webm", "Creator", "CC BY-SA 4.0",
            "https://creativecommons.org/licenses/by-sa/4.0/", "2026-11-05",
            width=1920, height=1080, duration_s=12, tags=["venice", "canal", "water"],
        )
        generic = VisualAssetCandidate(
            "generic", "Beautiful city", "Generic travel skyline",
            "video", "https://commons.wikimedia.org/wiki/File:Y.webm",
            "https://upload.wikimedia.org/y.webm", "Creator", "CC BY-SA 4.0",
            "https://creativecommons.org/licenses/by-sa/4.0/", "2026-11-05",
            width=1920, height=1080, duration_s=12,
        )
        narration = "Venice is a city built on canal water with gondolas."
        self.assertGreater(score_candidate(narration, relevant).overall,
                           score_candidate(narration, generic).overall)

    def test_factual_verifier_catches_conflict_and_unsourced_display(self) -> None:
        ledger = {
            "sources": [{"id": "s", "url": "https://example.org/source", "accessed_at": "2026-11-05", "reliability": "primary"}],
            "claims": [
                {"id": "a", "quantity": "peak", "value": 194, "unit": "cm", "display_value": 194,
                 "narration_value": 194, "source_ids": ["s"], "verified": True, "uncertainty": "datum"},
                {"id": "b", "quantity": "peak", "value": 187, "unit": "cm", "display_value": 187,
                 "narration_value": None, "source_ids": ["s"], "verified": True, "uncertainty": "other event"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            path.write_text(json.dumps(ledger), encoding="utf-8")
            report = verify_fact_ledger(path, displayed_text="194 cm and 241 cm", narration_text="194")
        codes = {f["code"] for f in report["findings"]}
        self.assertIn("conflicting_numbers", codes)
        self.assertIn("unsourced_display_number", codes)
        self.assertTrue(report["approval_blocked"])

    def test_visual_director_penalises_repeated_objective(self) -> None:
        text = "The lagoon islands and coast show where the city sits on water."
        first = rank_visual_treatments(text, [])
        repeated = rank_visual_treatments(text, [("map_context", "remotion")])
        first_map = next(score for score, rule, _ in first if rule[1] == "map_context")
        repeated_map = next(score for score, rule, _ in repeated if rule[1] == "map_context")
        self.assertLess(repeated_map, first_map)


if __name__ == "__main__":
    unittest.main()
