from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from geofactory import cli
from geofactory.agents.research_agent import (
    ResearchError, export_ledger, import_ledger, mark_claim_reviewed,
)
from geofactory.agents.script_agent import generate_evidence_script
from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.core.jobs import create_job, get_job, transition_job
from geofactory.media.asset_manager import register_asset
from geofactory.media.tts_engine import write_estimated_srt
from geofactory.quality.qa_engine import run_qa, validate_srt
from geofactory.scheduler.worker import process_offline_job, recover_and_process


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "data.sqlite3")
        self.db.initialize()
        self.config = FactoryConfig(
            root=self.root,
            database_path=self.root / "data.sqlite3",
            output_dir=self.root / "output",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_offline_demo_generates_package_and_blocks_approval(self) -> None:
        job = create_job(
            self.db, "Synthetic river towns", "How is this fictional region organized?",
            self.config.output_dir,
        )
        report = process_offline_job(self.db, self.config, job["id"])
        package = Path(job["output_dir"])
        self.assertTrue((package / "script.md").is_file())
        self.assertTrue((package / "source_ledger.json").is_file())
        self.assertTrue((package / "asset_ledger.json").is_file())
        self.assertTrue((package / "metadata.json").is_file())
        metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["channel_name"], "CHANNEL_NAME_TBD")
        self.assertEqual(metadata["credits"], ["Produced by CHANNEL_NAME_TBD"])
        self.assertIn("Production credit: CHANNEL_NAME_TBD", (
            package / "attribution.md"
        ).read_text(encoding="utf-8"))
        self.assertTrue((package / "qa_report.md").is_file())
        self.assertTrue(report["approval_blocked"])
        self.assertEqual(get_job(self.db, job["id"])["status"], "qa_failed")

    def test_worker_processes_a_queued_job_sequentially(self) -> None:
        job = create_job(
            self.db, "Synthetic queued job", "What does this queue do?",
            self.config.output_dir,
        )
        self.assertEqual(recover_and_process(self.db, self.config, max_jobs=1), [job["id"]])
        self.assertEqual(get_job(self.db, job["id"])["status"], "qa_failed")

    def test_thumbnail_failure_after_render_returns_job_to_qa_failed(self) -> None:
        job = create_job(
            self.db, "Synthetic thumbnail failure", "Does a failed thumbnail recover?",
            self.config.output_dir,
        )
        for state in ("researching", "scripting", "awaiting_review", "rendering", "qa_failed"):
            transition_job(self.db, job["id"], state)
        audio = self.root / "music.mp3"
        audio.write_bytes(b"synthetic audio fixture")
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO assets
                   (id, job_id, title, publisher, path, origin_url, creator, licence,
                    attribution, commercial_use, file_sha256, retrieved_at, media_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'audio')""",
                (
                    "synthetic-music", job["id"], "Synthetic music", "Fixture",
                    str(audio), "https://example.invalid/music", "Fixture",
                    "CC0-1.0", "Fixture, CC0-1.0", "synthetic-hash",
                    "2000-01-01T00:00:00Z",
                ),
            )
        image = self.root / "asset.png"
        image.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8A"
            "AwMCAO+/pWQAAAAASUVORK5CYII="
        ))
        register_asset(
            self.db, job["id"], image, "https://example.invalid/synthetic.png",
            "Synthetic fixture", "CC0-1.0", "Synthetic fixture, CC0-1.0", True,
        )
        args = argparse.Namespace(config=None, command="render", job_id=job["id"])
        with (
            patch("geofactory.cli.load_config", return_value=self.config),
            patch("geofactory.cli._validate_narration_package"),
            patch(
                "geofactory.cli.render_video",
                return_value=Path(job["output_dir"]) / "final.mp4",
            ),
            patch(
                "geofactory.cli.make_thumbnail",
                side_effect=RuntimeError("thumbnail failed"),
            ) as thumbnail,
            self.assertRaisesRegex(RuntimeError, "thumbnail failed"),
        ):
            cli.run(args)
        self.assertEqual(thumbnail.call_args.kwargs["background"], image)
        recovered = get_job(self.db, job["id"])
        self.assertEqual(recovered["status"], "qa_failed")
        self.assertEqual(recovered["error"], "thumbnail failed")

    def test_research_ledger_requires_traceable_fact_sources(self) -> None:
        job = create_job(
            self.db, "Synthetic test topic", "A test question?", self.config.output_dir
        )
        valid = self.root / "ledger.json"
        valid.write_text(json.dumps({
            "sources": [{
                "id": "test-source", "title": "Synthetic fixture",
                "url": "https://example.invalid/synthetic-fixture",
                "publisher": "Synthetic test fixture — not a real publisher",
                "licence": "Synthetic fixture only; not a legal licence",
                "evidence": "Synthetic-only test datum: sample value is 7.",
            }],
            "claims": [{
                "id": "test-claim", "text": "Synthetic-only sample value is 7.",
                "kind": "fact", "source_ids": ["test-source"],
            }],
        }), encoding="utf-8")
        self.assertEqual(import_ledger(self.db, job["id"], valid), {"sources": 1, "claims": 1})
        self.assertEqual(import_ledger(self.db, job["id"], valid), {"sources": 1, "claims": 1})
        mark_claim_reviewed(self.db, job["id"], "test-claim", "Test Reviewer")
        export_ledger(self.db, job["id"], Path(job["output_dir"]) / "source_ledger.json")
        with self.db.connect() as conn:
            reviewed = conn.execute(
                "SELECT reviewed, reviewer FROM claims WHERE id = 'test-claim'"
            ).fetchone()
        self.assertEqual((reviewed["reviewed"], reviewed["reviewer"]), (1, "Test Reviewer"))
        with self.assertRaises(ResearchError):
            mark_claim_reviewed(self.db, job["id"], "missing-claim", "Test Reviewer")
        import_ledger(self.db, job["id"], valid)
        with self.db.connect() as conn:
            reset = conn.execute(
                "SELECT reviewed FROM claims WHERE id = 'test-claim'"
            ).fetchone()
        self.assertEqual(reset["reviewed"], 0)

        other_job = create_job(
            self.db, "Another synthetic topic", "Another question?", self.config.output_dir
        )
        with self.assertRaises(ResearchError):
            import_ledger(self.db, other_job["id"], valid)
        with self.db.connect() as conn:
            owner = conn.execute(
                "SELECT job_id FROM sources WHERE id = 'test-source'"
            ).fetchone()
        self.assertEqual(owner["job_id"], job["id"])

        invalid = self.root / "invalid.json"
        invalid.write_text(json.dumps({
            "sources": [],
            "claims": [{"text": "Unsupported", "kind": "fact", "source_ids": []}],
        }), encoding="utf-8")
        with self.assertRaises(ResearchError):
            import_ledger(self.db, job["id"], invalid)

    def test_qa_requires_per_claim_human_review_and_synced_ledger(self) -> None:
        job = create_job(
            self.db, "Synthetic claim review test", "Does review unblock claims?",
            self.config.output_dir,
        )
        process_offline_job(self.db, self.config, job["id"])
        package = Path(job["output_dir"])
        ledger = self.root / "review-ledger.json"
        ledger.write_text(json.dumps({
            "sources": [{
                "id": "review-source", "title": "Synthetic fixture",
                "url": "https://example.invalid/review-fixture",
                "publisher": "Synthetic test fixture",
                "licence": "Synthetic fixture only; not a legal licence",
                "evidence": "Synthetic-only test datum.",
            }],
            "claims": [{
                "id": "review-claim", "text": "A synthetic test datum.",
                "kind": "fact", "source_ids": ["review-source"],
            }],
        }), encoding="utf-8")
        import_ledger(self.db, job["id"], ledger)
        export_ledger(self.db, job["id"], package / "source_ledger.json")
        (package / "script.md").write_text(
            "## Narration\nA synthetic test datum. [review-claim]\n",
            encoding="utf-8",
        )

        before = run_qa(self.db, job["id"], self.config)
        self.assertIn("claim_not_human_reviewed", {
            check["code"] for check in before["checks"]
        })

        mark_claim_reviewed(self.db, job["id"], "review-claim", "QA Tester")
        export_ledger(self.db, job["id"], package / "source_ledger.json")
        after = run_qa(self.db, job["id"], self.config)
        codes = {check["code"] for check in after["checks"]}
        self.assertNotIn("claim_not_human_reviewed", codes)
        self.assertNotIn("claim_ledger_mismatch", codes)

    def test_subtitle_generation_and_validation(self) -> None:
        path = self.root / "captions.srt"
        write_estimated_srt("One short line. Another short line.", path)
        self.assertEqual(validate_srt(path), [])
        path.write_text("1\n99:99:99,000 --> 00:00:00,000\nBad\n", encoding="utf-8")
        self.assertTrue(validate_srt(path))

    def test_local_script_draft_requires_word_count_and_known_claim_ids(self) -> None:
        job = create_job(
            self.db, "Synthetic test topic", "How does the fictional place work?",
            self.config.output_dir,
        )
        ledger = self.root / "script-ledger.json"
        ledger.write_text(json.dumps({
            "sources": [{
                "id": "src-1", "title": "Synthetic source",
                "url": "https://example.invalid/synthetic-source",
                "publisher": "Synthetic test fixture",
                "licence": "Synthetic fixture only; not a legal licence",
                "evidence": "Synthetic fact for a unit test only.",
            }],
            "claims": [{
                "id": "clm-1", "text": "A synthetic test claim.",
                "kind": "fact", "source_ids": ["src-1"],
            }],
        }), encoding="utf-8")
        import_ledger(self.db, job["id"], ledger)
        narration = "Careful geography brings several scales together. " * 240 + "[clm-1]"
        config = replace(self.config, local_llm_model="test-model")
        destination = Path(job["output_dir"]) / "script.md"
        with patch(
            "geofactory.agents.script_agent.generate_json",
            return_value={
                "narration": narration,
                "chapters": [{"title": "Context"}],
                "scene_plan": [{"narration_section": "Opening", "visual_direction": "Illustrative diagram"}],
            },
        ):
            words = generate_evidence_script(self.db, job["id"], destination, config)
        self.assertGreaterEqual(words, 1200)
        self.assertIn("[clm-1]", destination.read_text(encoding="utf-8"))
        with (
            patch(
                "geofactory.agents.script_agent.generate_groq_json",
                return_value={
                    "narration": narration,
                    "chapters": [{"title": "Context"}],
                    "scene_plan": [{
                        "narration_section": "Opening",
                        "visual_direction": "Illustrative diagram",
                    }],
                },
            ) as groq_generate,
            patch(
                "geofactory.agents.script_agent.generate_json",
                side_effect=AssertionError("Groq should take precedence when configured."),
            ),
        ):
            groq_config = replace(config, groq_api_key="test-only-key")
            groq_words = generate_evidence_script(
                self.db, job["id"], destination, groq_config
            )
        self.assertEqual(groq_words, words)
        groq_generate.assert_called_once()
        prompt = groq_generate.call_args.args[1]
        self.assertIn("within the first", prompt)
        self.assertIn("map, chart, or clearly sourced visual", prompt)
        self.assertIn("do not imitate or copy any existing creator", prompt)
        self.assertIn("disputed facts honestly", prompt)

    def test_documented_cli_dry_run_works_without_api_keys(self) -> None:
        config_path = self.root / "config.json"
        base = [sys.executable, "-m", "geofactory", "--config", str(config_path)]
        init = subprocess.run(base + ["init"], capture_output=True, text=True, timeout=30)
        self.assertEqual(init.returncode, 0, init.stderr)
        demo = subprocess.run(
            base + ["demo", "--topic", "Synthetic workflow test", "--question", "Is this only a demo?"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertIn("critical QA failures", demo.stdout)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        package_root = Path(config["root"]).resolve() / config["output_dir"]
        self.assertTrue(list(package_root.glob("*/qa_report.json")))


if __name__ == "__main__":
    unittest.main()
