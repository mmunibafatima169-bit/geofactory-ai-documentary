"""Regression test for smoke command function signatures."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSmokeSignatures(unittest.TestCase):
    """Test that smoke command uses correct function signatures."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.pythonpath = str(self.repo_root)

    def run_cli(self, args, env=None):
        """Run geofactory CLI as subprocess."""
        cmd = [sys.executable, "-m", "geofactory"] + args
        test_env = {"PYTHONPATH": self.pythonpath, **dict(env or {})}
        result = subprocess.run(cmd, capture_output=True, text=True, env=test_env, timeout=120)
        return result

    def test_smoke_no_code_errors(self):
        """Smoke test should not have any 'code_error' stages (TypeError, AttributeError, NameError)."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            # Smoke may fail at later stages without network/PIL/ffmpeg, but no code errors
            summary_path = out_dir / "summary.json"
            self.assertTrue(summary_path.exists(), "summary.json not created")
            summary = json.loads(summary_path.read_text())
            
            # Check that no stage has error_kind == "code_error"
            for stage_name, stage_info in summary["stages"].items():
                if stage_info["status"] == "FAIL":
                    error = stage_info.get("error", {})
                    # Network errors, missing deps are OK, but not TypeError/AttributeError/NameError
                    error_type = error.get("type", "")
                    self.assertNotIn(error_type, ["TypeError", "AttributeError", "NameError"],
                        f"Stage {stage_name} has code error: {error_type}: {error.get('message')}")

    def test_smoke_ledger_import_pass(self):
        """Ledger import stage should PASS with claims > 0."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            summary_path = out_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            self.assertIn("ledger_import", summary["stages"])
            stage = summary["stages"]["ledger_import"]
            self.assertEqual(stage["status"], "PASS")
            self.assertGreater(stage["details"].get("claims", 0), 0)

    def test_smoke_wikipedia_research_no_typeerror(self):
        """Wikipedia research should not raise TypeError about missing arguments."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            summary_path = out_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            if "wikipedia_research" in summary["stages"]:
                stage = summary["stages"]["wikipedia_research"]
                if stage["status"] == "FAIL":
                    error_type = stage.get("error", {}).get("type", "")
                    self.assertNotEqual(error_type, "TypeError",
                        f"wikipedia_research has TypeError: {stage.get('error', {}).get('message')}")

    def test_smoke_commons_assets_no_typeerror(self):
        """Commons assets should not raise TypeError about unexpected kwargs."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            summary_path = out_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            if "commons_assets" in summary["stages"]:
                stage = summary["stages"]["commons_assets"]
                if stage["status"] == "FAIL":
                    error_type = stage.get("error", {}).get("type", "")
                    self.assertNotEqual(error_type, "TypeError",
                        f"commons_assets has TypeError: {stage.get('error', {}).get('message')}")

    def test_smoke_map_build_no_typeerror(self):
        """Map build should not raise TypeError about unexpected kwargs."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            summary_path = out_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            if "map_build" in summary["stages"]:
                stage = summary["stages"]["map_build"]
                if stage["status"] == "FAIL":
                    error_type = stage.get("error", {}).get("type", "")
                    self.assertNotEqual(error_type, "TypeError",
                        f"map_build has TypeError: {stage.get('error', {}).get('message')}")

    def test_smoke_plan_documentary_no_typeerror(self):
        """Plan documentary should not raise TypeError about unexpected kwargs."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            summary_path = out_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            if "plan_documentary" in summary["stages"]:
                stage = summary["stages"]["plan_documentary"]
                if stage["status"] == "FAIL":
                    error_type = stage.get("error", {}).get("type", "")
                    self.assertNotEqual(error_type, "TypeError",
                        f"plan_documentary has TypeError: {stage.get('error', {}).get('message')}")

    def test_smoke_render_documentary_no_typeerror(self):
        """Render documentary should not raise TypeError about missing arguments."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--seconds", "10"])
            summary_path = out_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            if "render_documentary" in summary["stages"]:
                stage = summary["stages"]["render_documentary"]
                if stage["status"] == "FAIL":
                    error_type = stage.get("error", {}).get("type", "")
                    self.assertNotEqual(error_type, "TypeError",
                        f"render_documentary has TypeError: {stage.get('error', {}).get('message')}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
