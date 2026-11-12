"""
Full-documentary renderer: consumes DocumentaryPlan outputs (scene_manifest.json,
asset_allocations.json) and renders via FFmpeg with per-scene asset selection.

This connects the documentary planner to the production renderer.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from geofactory.core.config import FactoryConfig
from geofactory.media.asset_manager import ALLOWED_MEDIA_LICENSES, sha256_file
from geofactory.media.map_animation_engine import MapAnimationError, validate_map_scene
from geofactory.media.tts_engine import audio_duration_seconds

FRAME_RATE = 30


class DocumentaryRenderError(RuntimeError):
    """Raised when documentary render prerequisites or FFmpeg execution fails."""


def load_documentary_plan(package_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load scene manifest and asset allocations from package directory."""
    manifest_path = package_dir / "scene_manifest.json"
    allocations_path = package_dir / "asset_allocations.json"
    
    if not manifest_path.is_file():
        raise DocumentaryRenderError(f"Scene manifest not found: {manifest_path}")
    if not allocations_path.is_file():
        raise DocumentaryRenderError(f"Asset allocations not found: {allocations_path}")
    
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    allocations = json.loads(allocations_path.read_text(encoding="utf-8"))
    
    return manifest, allocations


def load_asset_records(package_dir: Path, db_records: list[dict]) -> dict[str, dict]:
    """Build a lookup of registered assets by local path."""
    records_by_path = {}
    for record in db_records:
        resolved = str(Path(str(record["path"])).resolve())
        records_by_path[resolved] = record
    return records_by_path


def validate_asset_record(record: dict, config: FactoryConfig) -> None:
    """Validate a single asset record for rendering."""
    resolved = Path(str(record["path"])).resolve()
    
    if record.get("licence") not in ALLOWED_MEDIA_LICENSES:
        raise DocumentaryRenderError(f"Media not registered with accepted licence: {resolved}")
    if not record.get("commercial_use"):
        raise DocumentaryRenderError(f"Media not cleared for commercial use: {resolved}")
    if not str(record.get("attribution", "")).strip():
        raise DocumentaryRenderError(f"Media missing attribution: {resolved}")
    if sha256_file(resolved) != record.get("file_sha256"):
        raise DocumentaryRenderError(f"Media file hash validation failed: {resolved}")


def probe_video(config: FactoryConfig, path: Path) -> dict[str, Any]:
    """Probe video file with ffprobe."""
    ffprobe = shutil.which(config.ffprobe)
    if not ffprobe:
        raise DocumentaryRenderError(f"FFprobe executable not found: {config.ffprobe}")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode:
        raise DocumentaryRenderError(f"FFprobe failed: {result.stderr[-1000:]}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DocumentaryRenderError("FFprobe returned invalid JSON.") from exc
    if not isinstance(parsed, dict) or not parsed.get("streams"):
        raise DocumentaryRenderError("FFprobe found no media streams.")
    return parsed


def _package_map_scenes(package_dir: Path) -> list[Path]:
    """Find generated map scene videos in the package directory."""
    maps_dir = package_dir / "maps"
    if not maps_dir.is_dir():
        return []
    scenes = []
    for f in sorted(maps_dir.glob("*.mp4")):
        try:
            validate_map_scene(f)
            scenes.append(f)
        except (OSError, MapAnimationError):
            continue
    return scenes


def render_documentary(
    config: FactoryConfig,
    manifest: dict[str, Any],
    allocations: dict[str, list[dict]],
    db_records: list[dict],
    narration_path: Path,
    subtitles_path: Path,
    destination: Path,
) -> Path:
    """
    Render a full documentary from the documentary plan.
    
    Uses the scene manifest's per-scene structure and the allocated assets per scene.
    Each scene gets its allocated asset(s) rendered at the exact scene timing.
    """
    # Validate inputs
    free_bytes = shutil.disk_usage(config.root).free
    required_bytes = int(config.minimum_free_disk_gb * 1024 ** 3)
    if free_bytes < required_bytes:
        raise DocumentaryRenderError(
            f"Low disk space: {free_bytes / 1024 ** 3:.2f} GiB free; "
            f"configured minimum is {config.minimum_free_disk_gb:.2f} GiB."
        )
    
    ffmpeg = shutil.which(config.ffmpeg)
    if not ffmpeg:
        raise DocumentaryRenderError(f"FFmpeg executable not found: {config.ffmpeg}")
    
    if not narration_path.is_file() or narration_path.stat().st_size == 0:
        raise DocumentaryRenderError(f"Narration WAV required: {narration_path}")
    if not subtitles_path.is_file() or subtitles_path.stat().st_size == 0:
        raise DocumentaryRenderError(f"SRT subtitles required: {subtitles_path}")
    
    # Load asset records
    records_by_path = load_asset_records(Path("."), db_records)
    
    # Get narration duration
    duration = audio_duration_seconds(narration_path, config.ffprobe)
    if duration <= 0:
        raise DocumentaryRenderError("Narration duration is not positive.")
    
    scenes = manifest.get("scenes", [])
    if not scenes:
        raise DocumentaryRenderError("Scene manifest has no scenes")
    
    # Build scene-to-asset mapping from allocations
    scene_assets = {}
    allocations_map = allocations.get("allocations", {})
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        allocated = allocations_map.get(scene_id, [])
        
        # Find the best available asset for this scene
        scene_asset = None
        for candidate in allocated:
            local_path = candidate.get("local_path", "")
            if not local_path:
                continue
            resolved = str(Path(local_path).resolve())
            if resolved in records_by_path:
                record = records_by_path[resolved]
                try:
                    validate_asset_record(record, config)
                    scene_asset = record
                    break
                except DocumentaryRenderError:
                    continue
        
        scene_assets[scene_id] = scene_asset
    
    # Also collect map scenes
    map_scenes = _package_map_scenes(narration_path.parent)
    map_scene_idx = 0
    
    # Build FFmpeg filter complex for per-scene rendering
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.mp4"
    )
    
    concat_inputs: list[str] = []
    filters: list[str] = []
    
    for idx, scene in enumerate(scenes):
        scene_id = scene["scene_id"]
        start_s = scene["start_s"]
        end_s = scene["end_s"]
        segment_duration = end_s - start_s
        
        asset = scene_assets.get(scene_id)
        visual_objective = scene.get("visual_objective", "photo_evidence")
        
        # Determine source: allocated asset, map scene, or error
        if asset:
            source_path = Path(str(asset["path"])).resolve()
            media_type = str(asset.get("media_type", "image"))
        elif visual_objective in ("map_context", "comparison_montage", "satellite_imagery") and map_scene_idx < len(map_scenes):
            source_path = map_scenes[map_scene_idx]
            media_type = "video"
            map_scene_idx += 1
        else:
            raise DocumentaryRenderError(
                f"No valid asset or map scene for scene {scene_id} "
                f"(objective: {visual_objective})"
            )
        
        if media_type == "video":
            # Video clip: trim to segment duration
            concat_inputs.extend(
                ["-t", f"{segment_duration:.6f}", "-i", str(source_path)]
            )
            filters.append(
                f"[{idx}:v]scale={config.width}:{config.height}:"
                f"force_original_aspect_ratio=increase,crop={config.width}:{config.height},"
                f"fps={FRAME_RATE},trim=end_frame={math.ceil(segment_duration * FRAME_RATE)},"
                f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{idx}]"
            )
        else:
            # Still image: Ken Burns with variety
            concat_inputs.extend(
                [
                    "-loop", "1", "-framerate", str(FRAME_RATE),
                    "-t", f"{segment_duration:.6f}", "-i", str(source_path),
                ]
            )
            # Alternating Ken Burns motion per scene
            motion_mode = idx % 4
            if motion_mode == 0:
                motion = (
                    "zoompan=z='min(zoom+0.00012,1.10)':"
                    "x='iw/2-(iw/zoom/2)+sin(on/250)*8':"
                    "y='ih/2-(ih/zoom/2)+cos(on/300)*5'"
                )
            elif motion_mode == 1:
                motion = (
                    "zoompan=z='if(gte(on,2),max(zoom-0.00012,1.0),1.10)':"
                    "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                )
            elif motion_mode == 2:
                motion = (
                    "zoompan=z=1.08:"
                    f"x='(iw-iw/zoom)*(on-1)/{max(1, math.ceil(segment_duration * FRAME_RATE))}':"
                    "y='ih/2-(ih/zoom/2)'"
                )
            else:
                motion = (
                    "zoompan=z=1.08:"
                    "x='iw/2-(iw/zoom/2)':"
                    f"y='(ih-ih/zoom)*(on-1)/{max(1, math.ceil(segment_duration * FRAME_RATE))}'"
                )
            filters.append(
                f"[{idx}:v]"
                f"scale={config.width}:{config.height}:force_original_aspect_ratio=increase,"
                f"crop={config.width}:{config.height},"
                f"{motion}:d=1:s={config.width}x{config.height}:fps={FRAME_RATE},"
                f"eq=saturation=1.05:contrast=1.03,vignette=angle=PI/6,"
                f"trim=end_frame={math.ceil(segment_duration * FRAME_RATE)},setpts=PTS-STARTPTS,"
                f"setsar=1,format=yuv420p[v{idx}]"
            )
    
    # Concatenate all scene videos
    joined = "".join(f"[v{idx}]" for idx in range(len(scenes)))
    filters.append(f"{joined}concat=n={len(scenes)}:v=1:a=0[vout]")
    
    # Audio: narration + optional music
    narration_idx = len(scenes)
    concat_inputs.extend(["-i", str(narration_path)])
    
    music_idx: int | None = None
    music_records = [r for r in db_records if r.get("media_type") == "audio" and r.get("commercial_use")]
    if music_records:
        music_idx = narration_idx + 1
        concat_inputs.extend(["-stream_loop", "-1", "-i", str(music_records[0]["path"])])
    
    subtitle_idx = narration_idx + 1 + int(music_idx is not None)
    concat_inputs.extend(["-i", str(subtitles_path)])
    
    # Audio mixing
    if music_idx is not None:
        filters.extend(
            [
                f"[{narration_idx}:a:0]volume=1.0[narration]",
                f"[{music_idx}:a:0]volume=0.1[music]",
                "[narration][music]amix=inputs=2:duration=first:dropout_transition=2,"
                "alimiter=limit=0.95[aout]",
            ]
        )
        audio_map = "[aout]"
    else:
        audio_map = f"{narration_idx}:a:0"
    
    command = [
        ffmpeg, "-y", "-v", "error",
        "-filter_complex_threads", "1",
        *concat_inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]",
        "-map", audio_map,
        "-map", f"{subtitle_idx}:0",
        "-t", f"{duration:.6f}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-threads", "2",
        "-c:a", "aac", "-b:a", "160k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng",
        "-movflags", "+faststart",
        str(temporary_output),
    ]
    
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=7200, check=False
        )
        if result.returncode:
            raise DocumentaryRenderError(
                f"FFmpeg render failed ({result.returncode}): {result.stderr[-3000:]}"
            )
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise DocumentaryRenderError("FFmpeg completed without producing a video file.")
        probe_video(config, temporary_output)
        temporary_output.replace(destination)
    except subprocess.TimeoutExpired as exc:
        temporary_output.unlink(missing_ok=True)
        raise DocumentaryRenderError("FFmpeg render exceeded its two-hour timeout.") from exc
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise
    
    return destination


def render_documentary_from_plan(
    config: FactoryConfig,
    job_id: str,
    package_dir: Path,
    destination: Path,
) -> Path:
    """
    High-level entry point: render documentary from the package's documentary plan.
    """
    # Load plan outputs
    manifest, allocations = load_documentary_plan(package_dir)
    
    # Load database asset records
    from geofactory.core.database import Database
    from geofactory.core.jobs import get_job
    
    db = Database(config.database_path)
    job = get_job(db, job_id)
    
    with db.connect() as conn:
        db_records = [dict(row) for row in conn.execute(
            "SELECT * FROM assets WHERE job_id = ? ORDER BY retrieved_at, id", (job_id,)
        )]
    
    # Validate narration and subtitles exist
    narration_path = package_dir / "narration.wav"
    subtitles_path = package_dir / "subtitles.srt"
    
    if not narration_path.is_file():
        raise DocumentaryRenderError(f"Narration not found: {narration_path}")
    if not subtitles_path.is_file():
        raise DocumentaryRenderError(f"Subtitles not found: {subtitles_path}")
    
    return render_documentary(
        config=config,
        manifest=manifest,
        allocations=allocations,
        db_records=db_records,
        narration_path=narration_path,
        subtitles_path=subtitles_path,
        destination=destination,
    )
