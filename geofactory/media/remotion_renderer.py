"""
Remotion Renderer: Dynamic documentary rendering via Remotion.

This module bridges the Python pipeline and the Remotion TypeScript compositions.
It generates the scene manifest JSON and invokes Remotion CLI to render.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geofactory.core.config import FactoryConfig
from geofactory.studio.scene_manifest import SceneManifest


@dataclass
class RemotionRenderResult:
    """Result of a Remotion render operation."""
    output_path: Path
    duration_seconds: float
    size_mb: float
    composition_id: str


class RemotionRendererError(RuntimeError):
    """Raised when Remotion rendering fails."""
    pass


def _find_remotion_project_root(config: FactoryConfig) -> Path | None:
    """Find the Remotion project root (studio/remotion)."""
    # Check relative to package root
    package_root = Path(__file__).resolve().parents[2]
    remotion_root = package_root / "studio" / "remotion"
    if (remotion_root / "package.json").is_file():
        return remotion_root
    return None


def _find_remotion_cli(remotion_root: Path) -> str | None:
    """Find the Remotion CLI executable (npx remotion)."""
    # Use npx from the remotion project directory
    node_modules_bin = remotion_root / "node_modules" / ".bin" / "remotion"
    if node_modules_bin.is_file():
        return str(node_modules_bin)
    # Fallback to npx
    return "npx"


def _ensure_remotion_deps(remotion_root: Path) -> bool:
    """Ensure Remotion dependencies are installed."""
    node_modules = remotion_root / "node_modules"
    if not node_modules.is_dir():
        print("Installing Remotion dependencies...")
        try:
            subprocess.run(
                ["npm", "install", "--no-audit", "--no-fund"],
                cwd=remotion_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RemotionRendererError(
                f"Failed to install Remotion dependencies: {e.stderr[-1000:]}"
            )
        except subprocess.TimeoutExpired:
            raise RemotionRendererError("npm install timed out after 5 minutes")
    return True


def _ensure_chrome(remotion_root: Path) -> bool:
    """Ensure Chrome is available for Remotion rendering."""
    # Check if Chrome is already available
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for path in chrome_paths:
        if Path(path).is_file():
            os.environ["PUPPETEER_EXECUTABLE_PATH"] = path
            return True
    
    # Try to use npx remotion browser ensure
    try:
        subprocess.run(
            ["npx", "remotion", "browser", "ensure"],
            cwd=remotion_root,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        pass
    except FileNotFoundError:
        pass
    
    return False


def prepare_scene_manifest_for_remotion(
    manifest: SceneManifest,
    output_dir: Path,
) -> Path:
    """
    Prepare the scene manifest for Remotion rendering.
    Writes a JSON file that Remotion can read via inputProps.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert SceneManifest to dict
    manifest_dict = {
        "job_id": manifest.job_id,
        "title": manifest.title,
        "fps": manifest.fps,
        "width": manifest.width,
        "height": manifest.height,
        "scenes": [
            {
                "scene_id": s.scene_id,
                "narration": s.narration,
                "start_s": s.start_s,
                "end_s": s.end_s,
                "visual_objective": s.visual_objective,
                "engine": s.engine,
                "animation_type": s.animation_type,
                "camera": s.camera,
                "text_overlays": s.text_overlays,
                "transition": s.transition,
                "sound_fx": s.sound_fx,
                "source_ids": s.source_ids,
                "rationale": s.rationale,
            }
            for s in manifest.scenes
        ],
    }
    
    manifest_path = output_dir / "scene_manifest.json"
    manifest_path.write_text(json.dumps(manifest_dict, indent=2), encoding="utf-8")
    
    return manifest_path


def render_with_remotion(
    config: FactoryConfig,
    job_id: str,
    package_dir: Path,
    composition_id: str = "DynamicDocumentary",
    output_filename: str = "remotion_output.mp4",
) -> RemotionRenderResult:
    """
    Render a documentary using Remotion.
    
    Args:
        config: Factory configuration
        job_id: Job identifier
        package_dir: Job package directory containing scene_manifest.json
        composition_id: Remotion composition ID to render
        output_filename: Output video filename
    
    Returns:
        RemotionRenderResult with output path and metadata
    """
    remotion_root = _find_remotion_project_root(config)
    if remotion_root is None:
        raise RemotionRendererError(
            "Remotion project not found. Expected at studio/remotion/"
        )
    
    # Ensure dependencies
    _ensure_remotion_deps(remotion_root)
    
    # Ensure Chrome
    if not _ensure_chrome(remotion_root):
        raise RemotionRendererError(
            "Chrome/Chromium not found. Remotion requires a browser for rendering. "
            "Install Chrome or run 'npx remotion browser ensure' in studio/remotion/"
        )
    
    # Verify scene manifest exists
    manifest_path = package_dir / "scene_manifest.json"
    if not manifest_path.is_file():
        raise RemotionRendererError(
            f"Scene manifest not found at {manifest_path}. Run plan-documentary first."
        )
    
    # Load manifest to get duration
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    
    # Calculate total duration from last scene
    total_duration_s = manifest_data["scenes"][-1]["end_s"] if manifest_data["scenes"] else 600
    total_frames = int(total_duration_s * manifest_data.get("fps", 30))
    
    # Output path
    output_path = package_dir / output_filename
    
    # Build remotion render command
    remotion_cli = _find_remotion_cli(remotion_root)
    
    # Use inputProps to pass the manifest
    input_props = json.dumps({"manifest": manifest_data})
    
    cmd = [
        remotion_cli, "render",
        f"src/index.ts",
        composition_id,
        str(output_path),
        f"--input-props={input_props}",
        f"--frames={total_frames}",
        f"--concurrency=4",
    ]
    
    print(f"Rendering with Remotion: {composition_id}")
    print(f"  Duration: {total_duration_s:.1f}s ({total_frames} frames)")
    print(f"  Output: {output_path}")
    
    try:
        # Run render with extended timeout for long videos
        timeout_seconds = max(3600, int(total_duration_s * 10))  # 10x realtime minimum
        result = subprocess.run(
            cmd,
            cwd=remotion_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
        print(result.stdout[-2000:] if result.stdout else "No stdout")
    except subprocess.TimeoutExpired as e:
        raise RemotionRendererError(
            f"Remotion render timed out after {timeout_seconds}s. "
            f"Video duration: {total_duration_s:.0f}s"
        ) from e
    except subprocess.CalledProcessError as e:
        raise RemotionRendererError(
            f"Remotion render failed (exit {e.returncode}): {e.stderr[-2000:]}"
        ) from e
    except FileNotFoundError as e:
        raise RemotionRendererError(
            f"Remotion CLI not found. Ensure Node.js and npm are installed: {e}"
        ) from e
    
    # Verify output
    if not output_path.is_file():
        raise RemotionRendererError(f"Remotion render completed but output not found: {output_path}")
    
    # Get file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    
    # Verify duration with FFprobe
    ffprobe = shutil.which(config.ffprobe)
    actual_duration = 0.0
    if ffprobe:
        try:
            probe_result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(output_path)],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if probe_result.returncode == 0:
                import json as json_stdlib
                probe_data = json_stdlib.loads(probe_result.stdout)
                actual_duration = float(probe_data.get("format", {}).get("duration", 0))
        except Exception:
            pass
    
    return RemotionRenderResult(
        output_path=output_path,
        duration_seconds=actual_duration or total_duration_s,
        size_mb=round(size_mb, 2),
        composition_id=composition_id,
    )


def render_documentary_remotion(
    config: FactoryConfig,
    job_id: str,
    package_dir: Path,
    output_path: Path,
) -> RemotionRenderResult:
    """
    High-level function to render a documentary via Remotion.
    Used by the pipeline orchestrator as an alternative to FFmpeg rendering.
    """
    # Prepare manifest for Remotion
    manifest_path = package_dir / "scene_manifest.json"
    if not manifest_path.is_file():
        raise RemotionRendererError(f"Scene manifest not found: {manifest_path}")
    
    # Load and validate manifest
    from geofactory.studio.scene_manifest import SceneManifest
    manifest = SceneManifest.load(manifest_path)
    manifest.validate()
    
    # Write manifest in Remotion format
    prepare_scene_manifest_for_remotion(manifest, package_dir)
    
    # Render
    result = render_with_remotion(
        config=config,
        job_id=job_id,
        package_dir=package_dir,
        composition_id="DynamicDocumentary",
        output_filename=output_path.name,
    )
    
    # Move to final location if different
    if result.output_path != output_path:
        shutil.move(str(result.output_path), str(output_path))
        result.output_path = output_path
    
    return result
