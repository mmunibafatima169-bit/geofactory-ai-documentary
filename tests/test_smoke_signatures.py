"""Regression test for smoke command function signatures."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSmokeSignatures(unittest.TestCase):
    """Test that smoke command uses correct function signatures."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            cls.out_dir = Path(tmp) / "smoke_out"
            cmd = [sys.executable, "-m", "geofactory", "smoke", "--out", str(cls.out_dir),
                   "--seconds", "60", "--offline"]
            cls.result = subprocess.run(cmd, capture_output=True, text=True,
                env={**os.environ, "PYTHONPATH": str(cls.repo_root)}, timeout=120)
            cls.summary_path = cls.out_dir / "summary.json"
            cls.summary = json.loads(cls.summary_path.read_text()) if cls.summary_path.exists() else {}

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.pythonpath = str(self.repo_root)

    def run_cli(self, args, env=None):
        """Run geofactory CLI as subprocess with --offline for network independence."""
        # Add --offline flag if not already present and it's a smoke command
        if args and args[0] == "smoke" and "--offline" not in args:
            args = args + ["--offline"]
        cmd = [sys.executable, "-m", "geofactory"] + args
        test_env = {**os.environ, "PYTHONPATH": str(self.repo_root), **dict(env or {})}
        result = subprocess.run(cmd, capture_output=True, text=True, env=test_env, timeout=120)
        return result

    def test_smoke_no_code_errors(self):
        """Smoke test should not have any 'code_error' stages (TypeError, AttributeError, NameError)."""
        expected = ["ledger_import", "wikipedia_research", "commons_assets", "map_build",
                    "script_generation", "plan_documentary"]
        for stage_name in expected:
            self.assertIn(stage_name, self.summary["stages"])
        for stage_name, stage_info in self.summary["stages"].items():
            self.assertNotEqual(
                stage_info.get("error_kind"),
                "code_error",
                f"Stage {stage_name} has code_error: {stage_info}",
            )

    def test_smoke_ledger_import_pass(self):
        """Ledger import stage should PASS with claims > 0."""
        stage = self.summary["stages"]["ledger_import"]
        self.assertEqual(stage["status"], "PASS")
        self.assertGreater(stage["details"].get("claims", 0), 0)

    def test_smoke_wikipedia_research_no_typeerror(self):
        """Wikipedia research should not raise TypeError about missing arguments."""
        stage = self.summary["stages"]["wikipedia_research"]
        self.assertNotEqual(stage.get("error_kind"), "code_error")

    def test_smoke_commons_assets_no_typeerror(self):
        """Commons assets should not raise TypeError about unexpected kwargs."""
        stage = self.summary["stages"]["commons_assets"]
        self.assertNotEqual(stage.get("error_kind"), "code_error")

    def test_smoke_map_build_no_typeerror(self):
        """Map build should not raise TypeError about unexpected kwargs."""
        stage = self.summary["stages"]["map_build"]
        self.assertNotEqual(stage.get("error_kind"), "code_error")

    def test_smoke_plan_documentary_no_typeerror(self):
        """Plan documentary should not raise TypeError about unexpected kwargs."""
        stage = self.summary["stages"]["plan_documentary"]
        self.assertNotEqual(stage.get("error_kind"), "code_error")
        self.assertEqual(stage["status"], "PASS")
        details = stage["details"]
        self.assertGreater(details.get("narration_words", 0), 0)
        self.assertGreaterEqual(details.get("scenes", 0), 2)

    def test_smoke_render_documentary_no_typeerror(self):
        """Render documentary should not raise TypeError about missing arguments."""
        stage = self.summary["stages"]["render_documentary"]
        self.assertNotEqual(stage.get("error_kind"), "code_error")

    def test_smoke_network_independence(self):
        """Smoke test with --offline should never make network calls."""
        self.assertEqual(self.summary["stages"]["ledger_import"]["status"], "PASS")
        self.assertEqual(self.summary["stages"]["wikipedia_research"]["status"], "SKIPPED")
        self.assertEqual(self.summary["stages"]["commons_assets"]["status"], "SKIPPED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
