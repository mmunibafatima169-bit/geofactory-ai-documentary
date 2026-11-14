from __future__ import annotations

import ast
import unittest
from pathlib import Path


class CLIAuditTests(unittest.TestCase):
    """AST-based audit for cli.py to detect shadowed imports."""

    def test_no_shadowed_imports_in_run_function(self):
        """Verify run() function has no local imports that shadow module-level names."""
        cli_path = Path(__file__).parent.parent / "geofactory" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Collect module-level imports
        module_imports = set()
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    module_imports.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_imports.add(alias.name)

        # Check run() functions for direct shadowing (not nested functions)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                # Only check direct body statements, not nested functions
                func_imports = set()
                for stmt in node.body:
                    if isinstance(stmt, ast.ImportFrom) and stmt.module:
                        for alias in stmt.names:
                            func_imports.add(alias.name)
                    elif isinstance(stmt, ast.Import):
                        for alias in stmt.names:
                            func_imports.add(alias.name)

                shadows = func_imports & module_imports
                if shadows:
                    self.fail(f"run() at line {node.lineno} has shadowed imports: {shadows}")

    def test_path_not_shadowed_in_run_function(self):
        """Specifically verify Path is not locally imported in run() function."""
        cli_path = Path(__file__).parent.parent / "geofactory" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                for stmt in node.body:  # Only direct body
                    if isinstance(stmt, ast.ImportFrom) and stmt.module == "pathlib":
                        for alias in stmt.names:
                            if alias.name == "Path":
                                self.fail(f"run() function has local 'from pathlib import Path' at line {stmt.lineno}")
                    elif isinstance(stmt, ast.Import):
                        for alias in stmt.names:
                            if alias.name == "Path":
                                self.fail(f"run() function has local 'import Path' at line {stmt.lineno}")

    def test_cmd_smoke_lazy_imports_at_start(self):
        """Verify _cmd_smoke lazy imports are all at function start (after docstring, before code)."""
        cli_path = Path(__file__).parent.parent / "geofactory" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_cmd_smoke":
                # Find first non-import, non-docstring statement
                first_code_line = None
                for stmt in node.body:
                    # Skip docstring (Expr with Constant/Str)
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        continue
                    if not (isinstance(stmt, ast.ImportFrom) or isinstance(stmt, ast.Import)):
                        first_code_line = stmt.lineno
                        break
                
                if first_code_line:
                    # Check for imports after first code line
                    late_imports = []
                    for stmt in node.body:
                        if isinstance(stmt, (ast.ImportFrom, ast.Import)) and stmt.lineno > first_code_line:
                            if isinstance(stmt, ast.ImportFrom) and stmt.module:
                                for alias in stmt.names:
                                    late_imports.append(f"{alias.name} (line {stmt.lineno})")
                            elif isinstance(stmt, ast.Import):
                                for alias in stmt.names:
                                    late_imports.append(f"{alias.name} (line {stmt.lineno})")
                    
                    if late_imports:
                        self.fail(f"_cmd_smoke has late imports after line {first_code_line}: {late_imports}")
                break


if __name__ == "__main__":
    unittest.main()
