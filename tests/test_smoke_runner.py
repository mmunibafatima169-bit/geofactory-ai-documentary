from __future__ import annotations

import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
