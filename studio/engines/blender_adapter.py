"""Blender 3D engine adapter.

Blender is optional and heavyweight; the adapter detects availability,
hands scenes our bundled Python scripts (`studio/blender/*.py`), and returns
rendered MP4 segments that the FFmpeg assembler treats like map scenes.
Nothing here installs Blender silently — run `python3 -m geofactory.studio.
engines.blender_adapter --bootstrap` to see install instructions.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

BLENDER_SCENE_DIR = Path(__file__).resolve().parents[2] / "blender"


class BlenderUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlenderStatus:
    available: bool
    executable: str | None
    version: str | None
    notes: str


def status() -> BlenderStatus:
    exe = shutil.which("blender")
    if not exe:
        return BlenderStatus(
            False, None, None,
            "Blender not on PATH. Linux: download the official tarball from "
            "https://download.blender.org/release/ and add it to PATH; it runs "
            "headless with `blender -b`. ~350 MB download, no root needed.",
        )
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        version = proc.stdout.splitlines()[0].strip() if proc.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        version = None
    return BlenderStatus(True, exe, version, "ok" if version else "present but failed --version")


def list_scenes() -> list[Path]:
    if not BLENDER_SCENE_DIR.is_dir():
        return []
    return sorted(BLENDER_SCENE_DIR.glob("*.py"))


def render_scene(
    scene_script: Path,
    output: Path,
    *,
    frames: int,
    width: int = 1920,
    height: int = 1080,
    timeout: int = 3600,
) -> Path:
    st = status()
    if not st.available or not st.executable:
        raise BlenderUnavailableError(st.notes)
    scene_script = Path(scene_script)
    if scene_script.parent.resolve() != BLENDER_SCENE_DIR.resolve():
        raise BlenderUnavailableError("Scene scripts must live in studio/blender/")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".frames")
    proc = subprocess.run(
        [
            st.executable, "-b", "-noaudio", "-P", str(scene_script), "--",
            "--frames", str(frames), "--width", str(width), "--height", str(height),
            "--out", str(tmp),
        ],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if proc.returncode != 0:
        raise BlenderUnavailableError(f"Blender exited {proc.returncode}: {proc.stderr[-400:]}")
    # ffmpeg-finalise the frame folder into an MP4 segment (assembly engine duty)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise BlenderUnavailableError("FFmpeg required to encode Blender frame output")
    enc = subprocess.run(
        [ffmpeg, "-y", "-v", "error", "-framerate", "30", "-i", str(tmp / "frame_%04d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(output)],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if enc.returncode != 0 or not output.is_file():
        raise BlenderUnavailableError(f"Blender frame encode failed: {enc.stderr[-400:]}")
    return output


if __name__ == "__main__":
    st = status()
    print("Blender:", "available" if st.available else "not installed")
    print(st.notes if not st.available else st.version)
    for scene in list_scenes():
        print(" scene:", scene.name)
