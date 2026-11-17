import json
from unittest.mock import patch
"""Regression tests for CLI smoke command and dispatch."""
import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCLIRegression(unittest.TestCase):
    """Test that CLI structure is correct after restoration."""

    def test_single_def_run(self):
        """cli.py must have exactly one 'def run' function."""
        with open("geofactory/cli.py") as f:
            tree = ast.parse(f.read())
        run_funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
        self.assertEqual(len(run_funcs), 1, "cli.py must have exactly one def run")

    def test_all_subcommands_handled(self):
        """All 37 subparser choices must be handled in run()."""
        with open("geofactory/cli.py") as f:
            tree = ast.parse(f.read())

        # Get subparser choices from build_parser
        parser_choices = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'attr') and node.func.attr == 'add_parser':
                if node.args and isinstance(node.args[0], ast.Constant):
                    parser_choices.add(node.args[0].value)

        # Get handled commands in run()
        handled = set()
        run_func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        for node in ast.walk(run_func):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    if isinstance(left, ast.Attribute) and left.attr == "command":
                        for comp in node.test.comparators:
                            if isinstance(comp, ast.Constant):
                                handled.add(comp.value)

        # Compare
        missing = parser_choices - handled
        extra = handled - parser_choices
        self.assertEqual(missing, set(), f"Subcommands missing from run(): {missing}")
        self.assertEqual(extra, set(), f"Extra handlers not in parser: {extra}")

    def test_singapore_ledger_single_reference(self):
        """The string 'singapore_ledger' must appear exactly once in code (not help)."""
        with open("geofactory/cli.py") as f:
            content = f.read()
        # Count non-comment, non-docstring occurrences in actual code
        # The help text has it once, the code path has it once
        code_refs = [i for i in range(len(content)) if content.startswith("singapore_ledger", i)]
        # Filter out the one in help text (contains "defaults to")
        # We expect exactly 2 total: 1 in help, 1 in code
        self.assertEqual(len(code_refs), 2, f"Expected 2 refs (1 help + 1 code), got {len(code_refs)}")


class TestCLISmokeSubprocess(unittest.TestCase):
    """Subprocess tests for smoke command."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out_dir = Path(cls.tmp.name) / "smoke_out"
        cmd = [sys.executable, "-m", "geofactory", "smoke", "--out", str(cls.out_dir),
               "--seconds", "60", "--offline"]
        cls.result = subprocess.run(cmd, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(cls.repo_root)}, timeout=120)
        cls.summary_path = cls.out_dir / "summary.json"
        cls.summary = json.loads(cls.summary_path.read_text()) if cls.summary_path.exists() else {}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_cli(self, args, env=None):
        """Run geofactory CLI as subprocess with --offline for network independence."""
        # Add --offline flag if not already present and it's a smoke command
        if args and args[0] == "smoke" and "--offline" not in args:
            args = args + ["--offline"]
        cmd = [sys.executable, "-m", "geofactory"] + args
        test_env = {**os.environ, "PYTHONPATH": str(self.repo_root), **dict(env or {})}
        result = subprocess.run(cmd, capture_output=True, text=True, env=test_env, timeout=60)
        return result

    def test_help_commands(self):
        """--help works for main and smoke."""
        for args in [["--help"], ["smoke", "--help"]]:
            result = self.run_cli(args)
            self.assertEqual(result.returncode, 0, f"Failed: {' '.join(args)}\n{result.stderr}")
            self.assertIn("usage:", result.stdout.lower())

    def test_init_command(self):
        """init command creates config and database."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            result = self.run_cli(["--config", str(config_path), "init"])
            self.assertEqual(result.returncode, 0, f"init failed: {result.stderr}")
            self.assertTrue(config_path.exists())
            # Database should be created
            db_path = Path(tmp) / "data" / "geofactory.sqlite3"
            self.assertTrue(db_path.exists(), f"Database not created at {db_path}")

    def test_smoke_ledger_import(self):
        """Smoke test imports ledger and records PASS with claims > 0."""
        self.assertTrue(self.summary_path.exists(), "summary.json not created")
        self.assertIn("ledger_import", self.summary["stages"])
        stage = self.summary["stages"]["ledger_import"]
        self.assertEqual(stage["status"], "PASS", f"ledger_import failed: {stage.get('error')}")
        self.assertGreater(stage["details"].get("claims", 0), 0, "No claims imported")
        self.assertIn("wikipedia_research", self.summary["stages"])
        self.assertEqual(self.summary["stages"]["wikipedia_research"]["status"], "SKIPPED")
        self.assertIn("commons_assets", self.summary["stages"])
        self.assertEqual(self.summary["stages"]["commons_assets"]["status"], "SKIPPED")
        for stage_name, stage in self.summary["stages"].items():
            self.assertNotEqual(stage.get("error_kind"), "code_error",
                f"{stage_name} has code_error")

    def test_smoke_invalid_ledger(self):
        """Smoke with nonexistent ledger creates summary.json and exits non-zero."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "smoke_out"
            result = self.run_cli(["smoke", "--out", str(out_dir), "--ledger", "/nonexistent.json"])
            self.assertNotEqual(result.returncode, 0, "Should fail with nonexistent ledger")
            summary_path = out_dir / "summary.json"
            self.assertTrue(summary_path.exists(), "summary.json not created on error")
            import json
            summary = json.loads(summary_path.read_text())
            # Should have init/preflight stage with FAIL
            init_stage = summary["stages"].get("init") or summary["stages"].get("preflight")
            self.assertIsNotNone(init_stage, "No init/preflight stage in summary")
            self.assertEqual(init_stage["status"], "FAIL")

    def test_smoke_network_independence(self):
        """Smoke test with --offline should never make network calls."""
        self.assertEqual(self.summary["stages"]["ledger_import"]["status"], "PASS")
        self.assertEqual(self.summary["stages"]["wikipedia_research"]["status"], "SKIPPED")
        self.assertEqual(self.summary["stages"]["commons_assets"]["status"], "SKIPPED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
