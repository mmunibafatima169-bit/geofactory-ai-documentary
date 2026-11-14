"""Tests for the pipeline orchestrator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Try to import the orchestrator - skip tests if PIL not available
try:
    from geofactory.pipeline.orchestrator import (
        PipelineStage,
        PipelineState,
        load_pipeline_state,
        save_pipeline_state,
        run_stage_with_timing,
        run_full_pipeline,
        STAGE_ORDER,
    )
    from geofactory.core.config import FactoryConfig
    from geofactory.core.database import Database
    from geofactory.core.jobs import create_job
    PIPELINE_AVAILABLE = True
except ImportError as e:
    if "PIL" in str(e) or "Image" in str(e):
        PIPELINE_AVAILABLE = False
    else:
        raise


@unittest.skipIf(not PIPELINE_AVAILABLE, "PIL not available in test environment")
class PipelineOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.package_dir = Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_state_serialization(self):
        state = PipelineState(
            job_id="test-job",
            current_stage=PipelineStage.PLAN,
            completed_stages=[PipelineStage.RESEARCH, PipelineStage.SCRIPT],
            stage_timings={"research": 5.2, "script": 12.1},
            config_overrides={"duration": 600.0},
        )
        
        save_pipeline_state(self.package_dir, state)
        loaded = load_pipeline_state(self.package_dir)
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.job_id, "test-job")
        self.assertEqual(loaded.current_stage, PipelineStage.PLAN)
        self.assertEqual(len(loaded.completed_stages), 2)
        self.assertEqual(loaded.stage_timings["research"], 5.2)
        self.assertEqual(loaded.config_overrides["duration"], 600.0)

    def test_pipeline_state_resume_detection(self):
        # No checkpoint
        state = load_pipeline_state(self.package_dir)
        self.assertIsNone(state)
        
        # With checkpoint
        state = PipelineState(job_id="test-job")
        save_pipeline_state(self.package_dir, state)
        loaded = load_pipeline_state(self.package_dir)
        self.assertIsNotNone(loaded)

    def test_stage_order(self):
        expected = [
            PipelineStage.RESEARCH,
            PipelineStage.SCRIPT,
            PipelineStage.FACT_CHECK,
            PipelineStage.PLAN,
            PipelineStage.NARRATE,
            PipelineStage.RENDER,
            PipelineStage.SHORTS,
            PipelineStage.QA,
        ]
        self.assertEqual(STAGE_ORDER, expected)

    def test_run_stage_with_timing_success(self):
        def dummy_func(x, y=10):
            return x + y
        
        result, elapsed = run_stage_with_timing(PipelineStage.RESEARCH, dummy_func, 5, y=3)
        self.assertEqual(result, 8)
        self.assertGreater(elapsed, 0)

    def test_run_stage_with_timing_failure(self):
        def failing_func():
            raise ValueError("test error")
        
        with self.assertRaises(Exception) as ctx:
            run_stage_with_timing(PipelineStage.SCRIPT, failing_func)
        self.assertIn("test error", str(ctx.exception))

    def test_run_full_pipeline_stage_order_includes_fact_check(self):
        """Verify FACT_CHECK stage is in the pipeline order after SCRIPT."""
        self.assertIn(PipelineStage.FACT_CHECK, STAGE_ORDER)
        research_idx = STAGE_ORDER.index(PipelineStage.RESEARCH)
        script_idx = STAGE_ORDER.index(PipelineStage.SCRIPT)
        fact_check_idx = STAGE_ORDER.index(PipelineStage.FACT_CHECK)
        plan_idx = STAGE_ORDER.index(PipelineStage.PLAN)
        self.assertLess(research_idx, script_idx)
        self.assertLess(script_idx, fact_check_idx)
        self.assertLess(fact_check_idx, plan_idx)


@unittest.skipIf(not PIPELINE_AVAILABLE, "PIL not available in test environment")
class PipelineOrchestratorIntegrationTests(unittest.TestCase):
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

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_checkpoint_save_load(self):
        from geofactory.pipeline.orchestrator import save_pipeline_state, load_pipeline_state
        
        state = PipelineState(job_id=self.job_id)
        save_pipeline_state(self.package_dir, state)
        
        loaded = load_pipeline_state(self.package_dir)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.job_id, self.job_id)


if __name__ == "__main__":
    unittest.main()
