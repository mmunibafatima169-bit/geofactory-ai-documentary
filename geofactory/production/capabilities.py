"""Honest executable/import probes. A successful probe never implies render quality."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Capability:
    name: str
    installed: bool
    runtime_verified: bool
    version: str | None
    executable_or_interpreter: str | None
    detail: str
    render_tested: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def executable_probe(name: str, executable: str, version_args: tuple[str, ...] = ("--version",)) -> Capability:
    path = shutil.which(executable) or (executable if Path(executable).is_file() else None)
    if not path:
        return Capability(name, False, False, None, None, "executable not found")
    try:
        proc = subprocess.run([path, *version_args], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return Capability(name, True, False, None, path, str(exc))
    output = (proc.stdout or proc.stderr).strip().splitlines()
    return Capability(name, True, proc.returncode == 0, output[0] if output else None, path, f"exit={proc.returncode}; version probe only")


def python_import_probe(name: str, interpreter: str, module: str, version_expression: str) -> Capability:
    code = f"import {module}; print({version_expression})"
    try:
        proc = subprocess.run([interpreter, "-c", code], capture_output=True, text=True, timeout=60, check=False, env=os.environ.copy())
    except (OSError, subprocess.SubprocessError) as exc:
        return Capability(name, False, False, None, interpreter, str(exc))
    version = proc.stdout.strip().splitlines()
    detail = proc.stderr.strip()[-500:] if proc.returncode else "import/version probe only; no render performed"
    return Capability(name, proc.returncode == 0 or "ModuleNotFoundError" not in proc.stderr, proc.returncode == 0, version[-1] if version else None, interpreter, detail)


def write_capability_report(capabilities: list[Capability], destination: Path) -> None:
    payload = {
        "scope": "Installation and non-rendering runtime probes only",
        "render_tested": False,
        "capabilities": [capability.to_dict() for capability in capabilities],
    }
    Path(destination).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
