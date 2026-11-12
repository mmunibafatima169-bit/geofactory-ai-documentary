"""
YouTube Shorts Generator: Creates 15-60 second vertical Shorts from documentary assets.

Uses the documentary plan's scene manifest and asset allocations to create
engaging vertical clips (9:16) with fast pacing, captions, and hook-driven structure.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geofactory.core.config import FactoryConfig
from geofactory.media.asset_manager import ALLOWED_MEDIA_LICENSES, sha256_file
from geofactory.media.map_animation_engine import MapAnimationError, validate_map_scene
from geofactory.media.tts_engine import audio_duration_seconds

SHORTS_FPS = 30
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920  # 9:16 vertical
MAX_SHORTS_DURATION = 60.0  # YouTube Shorts max
MIN_SHORTS_DURATION = 15.0


class ShortsRenderError(RuntimeError):
    """Raised when Shorts render prerequisites or FFmpeg execution fails."""


@dataclass
class ShortsPlan:
    """Plan for a single Short."""
    title: str
    hook_text: str
    scenes: list[dict[str, Any]]  # Subset of documentary scenes, re-timed
    total_duration: float
    narration_path: Path
    subtitles_path: Path
    music_path: Path | None = None


def load_documentary_plan(package_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load scene manifest and asset allocations from package directory."""
    manifest_path = package_dir / "scene_manifest.json"
    allocations_path = package_dir / "asset_allocations.json"
    
    if not manifest_path.is_file():
        raise ShortsRenderError(f"Scene manifest not found: {manifest_path}")
    if not allocations_path.is_file():
        raise ShortsRenderError(f"Asset allocations not found: {allocations_path}")
    
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    allocations = json.loads(allocations_path.read_text(encoding="utf-8"))
    
    return manifest, allocations


def load_asset_records(db_records: list[dict]) -> dict[str, dict]:
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
        raise ShortsRenderError(f"Media not registered with accepted licence: {resolved}")
    if not record.get("commercial_use"):
        raise ShortsRenderError(f"Media not cleared for commercial use: {resolved}")
    if not str(record.get("attribution", "")).strip():
        raise ShortsRenderError(f"Media missing attribution: {resolved}")
    if sha256_file(resolved) != record.get("file_sha256"):
        raise ShortsRenderError(f"Media file hash validation failed: {resolved}")


def probe_video(config: FactoryConfig, path: Path) -> dict[str, Any]:
    """Probe video file with ffprobe."""
    ffprobe = shutil.which(config.ffprobe)
    if not ffprobe:
        raise ShortsRenderError(f"FFprobe executable not found: {config.ffprobe}")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode:
        raise ShortsRenderError(f"FFprobe failed: {result.stderr[-1000:]}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ShortsRenderError("FFprobe returned invalid JSON.") from exc
    if not isinstance(parsed, dict) or not parsed.get("streams"):
        raise ShortsRenderError("FFprobe found no media streams.")
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


def create_shorts_plan(
    manifest: dict[str, Any],
    allocations: dict[str, list[dict]],
    db_records: list[dict],
    package_dir: Path,
    target_duration: float = 45.0,
    hook_text: str | None = None,
) -> ShortsPlan:
    """
    Create a Shorts plan from the documentary manifest.
    
    Selects the most engaging scenes (opening hook, key visual moments, conclusion)
    and re-times them for vertical fast-paced format.
    """
    scenes = manifest.get("scenes", [])
    if not scenes:
        raise ShortsRenderError("Scene manifest has no scenes")
    
    if not MIN_SHORTS_DURATION <= target_duration <= MAX_SHORTS_DURATION:
        raise ShortsRenderError(f"Target duration must be {MIN_SHORTS_DURATION}-{MAX_SHORTS_DURATION}s")
    
    # Score scenes for Shorts suitability
    scored_scenes = []
    for scene in scenes:
        score = 0
        obj = scene.get("visual_objective", "")
        # Prioritize: cold_open, map_zoom, engineering_demo, comparison_montage, closing_beat
        if obj in ("cold_open", "map_zoom", "map_context"):
            score += 30
        elif obj in ("engineering_demo", "comparison_montage", "data_chart"):
            score += 25
        elif obj in ("archival_footage", "cinematic_footage", "satellite_imagery"):
            score += 20
        elif obj == "closing_beat":
            score += 30  # Always include conclusion
        elif obj == "title_card":
            score += 15
        else:
            score += 10
        
        # Prefer scenes with allocated assets
        scene_id = scene["scene_id"]
        if allocations.get("allocations", {}).get(scene_id):
            score += 15
        
        # Prefer shorter scenes (easier to fit)
        duration = scene["end_s"] - scene["start_s"]
        if duration <= 15:
            score += 10
        elif duration <= 25:
            score += 5
        
        scored_scenes.append((score, scene))
    
    scored_scenes.sort(key=lambda x: x[0], reverse=True)
    
    # Select scenes to fit target duration
    selected = []
    total_dur = 0.0
    for score, scene in scored_scenes:
        scene_dur = scene["end_s"] - scene["start_s"]
        # Cap individual scene duration for Shorts
        capped_dur = min(scene_dur, 10.0)
        if total_dur + capped_dur <= target_duration:
            selected.append(scene)
            total_dur += capped_dur
        if total_dur >= target_duration * 0.9:  # Allow some slack
            break
    
    if not selected:
        # Fallback: take first N scenes
        selected = scenes[:3]
        total_dur = sum(min(s["end_s"] - s["start_s"], 10.0) for s in selected)
    
    # Re-time scenes for Shorts pacing (faster cuts)
    shorts_scenes = []
    cursor = 0.0
    for scene in selected:
        orig_dur = scene["end_s"] - scene["start_s"]
        shorts_dur = min(orig_dur, 8.0)  # Max 8s per scene in Shorts
        shorts_scenes.append({
            **scene,
            "shorts_start": cursor,
            "shorts_end": cursor + shorts_dur,
            "shorts_duration": shorts_dur,
        })
        cursor += shorts_dur
    
    # Generate hook text if not provided
    if hook_text is None:
        first_scene = scenes[0] if scenes else {}
        hook_text = first_scene.get("narration", "Watch this!")[:80]
    
    return ShortsPlan(
        title=manifest.get("title", "Documentary Short"),
        hook_text=hook_text,
        scenes=shorts_scenes,
        total_duration=cursor,
        narration_path=package_dir / "narration.wav",
        subtitles_path=package_dir / "subtitles.srt",
        music_path=package_dir / "music.wav" if (package_dir / "music.wav").is_file() else None,
    )


def render_shorts(
    config: FactoryConfig,
    plan: ShortsPlan,
    allocations: dict[str, list[dict]],
    db_records: list[dict],
    package_dir: Path,
    destination: Path,
) -> Path:
    """Render a vertical Shorts video from the plan."""
    # Validate inputs
    free_bytes = shutil.disk_usage(config.root).free
    required_bytes = int(config.minimum_free_disk_gb * 1024 ** 3)
    if free_bytes < required_bytes:
        raise ShortsRenderError(
            f"Low disk space: {free_bytes / 1024 ** 3:.2f} GiB free; "
            f"configured minimum is {config.minimum_free_disk_gb:.2f} GiB."
        )
    
    ffmpeg = shutil.which(config.ffmpeg)
    if not ffmpeg:
        raise ShortsRenderError(f"FFmpeg executable not found: {config.ffmpeg}")
    
    if not plan.narration_path.is_file() or plan.narration_path.stat().st_size == 0:
        raise ShortsRenderError(f"Narration WAV required: {plan.narration_path}")
    if not plan.subtitles_path.is_file() or plan.subtitles_path.stat().st_size == 0:
        raise ShortsRenderError(f"SRT subtitles required: {plan.subtitles_path}")
    
    # Load asset records
    records_by_path = load_asset_records(db_records)
    
    # Get actual narration duration (may be longer than plan)
    narration_dur = audio_duration_seconds(plan.narration_path, config.ffprobe)
    actual_duration = min(plan.total_duration, narration_dur, MAX_SHORTS_DURATION)
    
    # Build scene-to-asset mapping
    scene_assets = {}
    allocations_map = allocations.get("allocations", {})
    
    for scene in plan.scenes:
        scene_id = scene["scene_id"]
        allocated = allocations_map.get(scene_id, [])
        
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
                except ShortsRenderError:
                    continue
        
        scene_assets[scene_id] = scene_asset
    
    # Map scenes
    map_scenes = _package_map_scenes(package_dir)
    map_scene_idx = 0
    
    # Build FFmpeg filter complex for vertical 9:16 rendering
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.mp4"
    )
    
    concat_inputs: list[str] = []
    filters: list[str] = []
    
    for idx, scene in enumerate(plan.scenes):
        scene_id = scene["scene_id"]
        segment_duration = scene["shorts_duration"]
        
        asset = scene_assets.get(scene_id)
        visual_objective = scene.get("visual_objective", "photo_evidence")
        
        # Determine source
        if asset:
            source_path = Path(str(asset["path"])).resolve()
            media_type = str(asset.get("media_type", "image"))
        elif visual_objective in ("map_context", "comparison_montage", "satellite_imagery") and map_scene_idx < len(map_scenes):
            source_path = map_scenes[map_scene_idx]
            media_type = "video"
            map_scene_idx += 1
        else:
            raise ShortsRenderError(
                f"No valid asset or map scene for scene {scene_id} "
                f"(objective: {visual_objective})"
            )
        
        if media_type == "video":
            concat_inputs.extend(
                ["-t", f"{segment_duration:.6f}", "-i", str(source_path)]
            )
            filters.append(
                f"[{idx}:v]scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:"
                f"force_original_aspect_ratio=increase,crop={SHORTS_WIDTH}:{SHORTS_HEIGHT},"
                f"fps={SHORTS_FPS},trim=end_frame={math.ceil(segment_duration * SHORTS_FPS)},"
                f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{idx}]"
            )
        else:
            concat_inputs.extend(
                [
                    "-loop", "1", "-framerate", str(SHORTS_FPS),
                    "-t", f"{segment_duration:.6f}", "-i", str(source_path),
                ]
            )
            # Fast Ken Burns for Shorts
            motion_mode = idx % 3
            if motion_mode == 0:
                motion = "zoompan=z='min(zoom+0.0003,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            elif motion_mode == 1:
                motion = f"zoompan=z=1.12:x='(iw-iw/zoom)*(on-1)/{max(1, math.ceil(segment_duration * SHORTS_FPS))}':y='ih/2-(ih/zoom/2)'"
            else:
                motion = f"zoompan=z=1.12:x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(on-1)/{max(1, math.ceil(segment_duration * SHORTS_FPS))}'"
            filters.append(
                f"[{idx}:v]"
                f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={SHORTS_WIDTH}:{SHORTS_HEIGHT},"
                f"{motion}:d=1:s={SHORTS_WIDTH}x{SHORTS_HEIGHT}:fps={SHORTS_FPS},"
                f"eq=saturation=1.1:contrast=1.05,"
                f"trim=end_frame={math.ceil(segment_duration * SHORTS_FPS)},setpts=PTS-STARTPTS,"
                f"setsar=1,format=yuv420p[v{idx}]"
            )
    
    # Add hook text overlay on first scene
    if plan.hook_text:
        # We'll add drawtext for hook on first scene
        hook_escaped = plan.hook_text.replace("'", "\\'").replace(":", "\\:")
        filters[0] = filters[0].replace(
            "format=yuv420p[v0]",
            f"drawtext=text='{hook_escaped}':fontsize=60:fontcolor=white:"
            f"x=(w-text_w)/2:y=h*0.15:borderw=3:bordercolor=black,"
            f"format=yuv420p[v0]"
        )
    
    # Concatenate all scene videos
    joined = "".join(f"[v{idx}]" for idx in range(len(plan.scenes)))
    filters.append(f"{joined}concat=n={len(plan.scenes)}:v=1:a=0[vout]")
    
    # Audio: narration (trimmed to Shorts duration) + optional music
    narration_idx = len(plan.scenes)
    concat_inputs.extend(["-t", f"{actual_duration:.6f}", "-i", str(plan.narration_path)])
    
    music_idx: int | None = None
    if plan.music_path and plan.music_path.is_file():
        music_idx = narration_idx + 1
        concat_inputs.extend(["-stream_loop", "-1", "-i", str(plan.music_path)])
    
    subtitle_idx = narration_idx + 1 + int(music_idx is not None)
    concat_inputs.extend(["-i", str(plan.subtitles_path)])
    
    # Audio mixing
    if music_idx is not None:
        filters.extend(
            [
                f"[{narration_idx}:a:0]volume=1.0,atrim=0:{actual_duration:.6f}[narration]",
                f"[{music_idx}:a:0]volume=0.08[music]",
                "[narration][music]amix=inputs=2:duration=first:dropout_transition=1,"
                "alimiter=limit=0.95[aout]",
            ]
        )
        audio_map = "[aout]"
    else:
        filters.append(f"[{narration_idx}:a:0]atrim=0:{actual_duration:.6f},volume=1.0[aout]")
        audio_map = "[aout]"
    
    # Subtitles: need to re-time for Shorts (complex - simplified here)
    command = [
        ffmpeg, "-y", "-v", "error",
        "-filter_complex_threads", "1",
        *concat_inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]",
        "-map", audio_map,
        "-map", f"{subtitle_idx}:0",
        "-t", f"{actual_duration:.6f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-threads", "2",
        "-c:a", "aac", "-b:a", "128k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng",
        "-movflags", "+faststart",
        "-vf", f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:force_original_aspect_ratio=increase,crop={SHORTS_WIDTH}:{SHORTS_HEIGHT},setsar=1",
        str(temporary_output),
    ]
    
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=1800, check=False
        )
        if result.returncode:
            raise ShortsRenderError(
                f"FFmpeg render failed ({result.returncode}): {result.stderr[-3000:]}"
            )
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise ShortsRenderError("FFmpeg completed without producing a video file.")
        probe_video(config, temporary_output)
        temporary_output.replace(destination)
    except subprocess.TimeoutExpired as exc:
        temporary_output.unlink(missing_ok=True)
        raise ShortsRenderError("FFmpeg render exceeded its 30-minute timeout.") from exc
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise
    
    return destination


def generate_shorts_from_documentary(
    config: FactoryConfig,
    job_id: str,
    package_dir: Path,
    destination: Path,
    target_duration: float = 45.0,
    hook_text: str | None = None,
) -> Path:
    """
    High-level entry point: generate Shorts from documentary package.
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
    
    # Create Shorts plan
    plan = create_shorts_plan(
        manifest=manifest,
        allocations=allocations,
        db_records=db_records,
        package_dir=package_dir,
        target_duration=target_duration,
        hook_text=hook_text,
    )
    
    return render_shorts(
        config=config,
        plan=plan,
        allocations=allocations,
        db_records=db_records,
        package_dir=package_dir,
        destination=destination,
    )
