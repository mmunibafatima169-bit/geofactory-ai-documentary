"""Manim Community engine adapter for technical explanations.

Manim needs Cairo/Pango system libraries; it is optional. This adapter detects
availability, renders a scene class from studio/manim/*.py, and returns an MP4
segment for final assembly. Install notes are provided instead of silent
installation.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

MANIM_SCENE_DIR = Path(__file__).resolve().parents[2] / "manim"


class ManimUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManimStatus:
    available: bool
    executable: str | None
    version: str | None
    notes: str


def status() -> ManimStatus:
    exe = shutil.which("manim") or shutil.which("manimCE")
    if not exe:
        return ManimStatus(
            False, None, None,
            "Manim CE not on PATH. Install with `pip install manim` plus system "
            "Cairo/Pango (Debian: libcairo2-dev libpango1.0-dev pkg-config). Those "
            "system packages need root; use your own machine or a provisioned image.",
        )
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60)
        version = proc.stdout.strip() if proc.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        version = None
    return ManimStatus(True, exe, version, "ok" if version else "present but failed --version")


def render_scene(
    scene_file: Path,
    scene_name: str,
    output: Path,
    *,
    quality: str = "l",          # l=480p preview, h=1080p final
    timeout: int = 1800,
) -> Path:
    st = status()
    if not st.available or not st.executable:
        raise ManimUnavailableError(st.notes)
    scene_file = Path(scene_file)
    if scene_file.parent.resolve() != MANIM_SCENE_DIR.resolve():
        raise ManimUnavailableError("Scene files must live in studio/manim/")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    media_dir = output.parent / f".{scene_name}.media"
    quality_flag = {"l": "-ql", "m": "-qm", "h": "-qh"}[quality]
    proc = subprocess.run(
        [st.executable, quality_flag, "--media_dir", str(media_dir),
         "-o", scene_name, str(scene_file), scene_name],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if proc.returncode != 0:
        raise ManimUnavailableError(f"Manim exited {proc.returncode}: {proc.stderr[-400:]}")
    produced = sorted(media_dir.rglob(f"{scene_name}.mp4"))
    if not produced:
        raise ManimUnavailableError("Manim finished but produced no scene file")
    produced[0].replace(output)
    return output


if __name__ == "__main__":
    st = status()
    print("Manim:", "available" if st.available else "not installed")
    print(st.notes if not st.available else st.version)
