from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLISmokeRegressionTests(unittest.TestCase):
    """Regression tests for CLI commands to ensure they don't crash due to shadowed imports."""

    def _run_cli(self, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
        """Run geofactory CLI command and return result."""
        env = os.environ.copy()
        env["PYTHONPATH"] = "/root/geofactory-ai-documentary"
        cmd = [sys.executable, "-m", "geofactory"] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or Path.cwd(), env=env)

    def test_help_command(self):
        """`python -m geofactory --help` should exit 0 and print usage."""
        result = self._run_cli(["--help"])
        self.assertEqual(result.returncode, 0, 
            f"geofactory --help failed with exit code {result.returncode}: {result.stderr}")
        self.assertIn("usage:", result.stdout.lower())
        self.assertIn("geofactory", result.stdout.lower())

    def test_smoke_help_command(self):
        """`python -m geofactory smoke --help` should exit 0 without requiring PIL."""
        result = self._run_cli(["smoke", "--help"])
        self.assertEqual(result.returncode, 0,
            f"geofactory smoke --help failed with exit code {result.returncode}: {result.stderr}")
        self.assertIn("smoke", result.stdout.lower())
        self.assertIn("--topic", result.stdout)
        self.assertIn("--seconds", result.stdout)

    def test_init_command(self):
        """`python -m geofactory init` should work in a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            result = self._run_cli(["init"], cwd=tmp_path)
            self.assertEqual(result.returncode, 0,
                f"geofactory init failed with exit code {result.returncode}: {result.stderr}")
            # Verify config.json and database were created
            self.assertTrue((tmp_path / "config.json").exists(), "config.json not created")
            self.assertTrue((tmp_path / "data" / "geofactory.sqlite3").exists(), "database not created")


if __name__ == "__main__":
    unittest.main()
