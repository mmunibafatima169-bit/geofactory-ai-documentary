"""Memory-bounded FFmpeg Ken Burns rendering with soft subtitles and narration sync."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from pathlib import Path

from geofactory.core.config import FactoryConfig
from geofactory.media.asset_manager import ALLOWED_MEDIA_LICENSES, sha256_file
from geofactory.media.map_animation_engine import MapAnimationError, validate_map_scene
from geofactory.media.tts_engine import audio_duration_seconds

FRAME_RATE = 30


class RenderError(RuntimeError):
    """Raised when render prerequisites or FFmpeg execution fails."""


def render_video(
    config: FactoryConfig,
    images: list[Path],
    narration: Path,
    destination: Path,
    asset_records: list[dict[str, object]],
    subtitles: Path | None = None,
    scene_videos: list[Path] | None = None,
) -> Path:
    free_bytes = shutil.disk_usage(config.root).free
    required_bytes = int(config.minimum_free_disk_gb * 1024 ** 3)
    if free_bytes < required_bytes:
        raise RenderError(
            f"Low disk space: {free_bytes / 1024 ** 3:.2f} GiB free; "
            f"configured minimum is {config.minimum_free_disk_gb:.2f} GiB."
        )
    ffmpeg = shutil.which(config.ffmpeg)
    if not ffmpeg:
        raise RenderError(f"FFmpeg executable not found: {config.ffmpeg}")
    scene_videos = scene_videos or []
    if not images and not scene_videos:
        raise RenderError("At least one licensed visual asset or verified map scene is required.")
    if not narration.is_file() or narration.stat().st_size == 0:
        raise RenderError("A non-empty narration WAV file is required.")
    subtitles = subtitles or destination.with_name("subtitles.srt")
    if not subtitles.is_file() or not subtitles.stat().st_size:
        raise RenderError(f"A generated SRT subtitle file is required: {subtitles}")

    records_by_path = {
        str(Path(str(record["path"])).resolve()): record for record in asset_records
    }
    image_records: list[dict[str, object]] = []
    video_records: list[dict[str, object]] = []
    music_records: list[dict[str, object]] = []
    map_records: list[dict[str, object]] = []
    for path in scene_videos:
        try:
            resolved = path.resolve(strict=True)
            map_manifest = validate_map_scene(resolved)
        except (OSError, MapAnimationError) as exc:
            raise RenderError(f"Generated map scene failed validation: {exc}") from exc
        map_records.append({
            "path": str(resolved),
            "media_type": "video",
            "licence": map_manifest["licence"],
            "commercial_use": True,
            "attribution": (
                f"Made with {map_manifest['dataset_name']} "
                f"{map_manifest['dataset_version']} ({map_manifest['licence']})"
            ),
            "file_sha256": map_manifest["segment_sha256"],
        })
    for path in images:
        resolved = path.resolve(strict=True)
        record = records_by_path.get(str(resolved))
        if record is None or record.get("licence") not in ALLOWED_MEDIA_LICENSES:
            raise RenderError(f"Media is not registered with an accepted licence: {path}")
        if (
            not record.get("commercial_use")
            or not str(record.get("attribution", "")).strip()
            or sha256_file(resolved) != record.get("file_sha256")
        ):
            raise RenderError(f"Media rights or file hash validation failed: {path}")
        media_type = str(record.get("media_type", "image"))
        if media_type == "video":
            video_records.append(record)
        elif media_type == "audio":
            music_records.append(record)
        elif media_type == "image":
            image_records.append(record)
        else:
            raise RenderError(f"Unsupported registered media type {media_type!r}: {path}")
    if len(music_records) > 1:
        raise RenderError("Register at most one background music track per render.")
    if not video_records and not image_records and not map_records:
        raise RenderError("At least one licensed video clip or still image is required.")
    video_durations: list[tuple[dict[str, object], float]] = []
    if map_records or video_records:
        for record in [*map_records, *video_records]:
            if Path(str(record["path"])).suffix.lower() != ".mp4":
                raise RenderError("Registered stock video clips must use the validated MP4 format.")
            probe = probe_video(config, Path(str(record["path"])))
            try:
                clip_duration = float(probe.get("format", {}).get("duration", 0))
            except (TypeError, ValueError, AttributeError) as exc:
                raise RenderError("FFprobe returned an invalid stock-video duration.") from exc
            if clip_duration <= 0:
                raise RenderError("A registered stock clip has no positive duration.")
            video_durations.append((record, clip_duration))
    if music_records:
        probe_video(config, Path(str(music_records[0]["path"])))

    duration = audio_duration_seconds(narration, config.ffprobe)
    if duration <= 0:
        raise RenderError("Narration duration is not positive.")
    total_frames = max(1, math.ceil(duration * FRAME_RATE))
    frames_remaining = total_frames
    video_segments: list[tuple[dict[str, object], int]] = []
    for record, clip_duration in video_durations:
        frame_count = min(math.ceil(clip_duration * FRAME_RATE), frames_remaining)
        if frame_count > 0:
            video_segments.append((record, frame_count))
            frames_remaining -= frame_count
        if frames_remaining == 0:
            break
    # Still-image pacing: no single photo may hold the screen longer than a
    # documentary beat (~22 s); assets rotate round-robin when more narration
    # time must be covered, and a floor (~12 s) keeps cuts from feeling jumpy.
    min_still_frames = 12 * FRAME_RATE
    max_still_frames = 22 * FRAME_RATE
    image_segments: list[tuple[dict[str, object], int]] = []
    if frames_remaining:
        if not image_records:
            raise RenderError(
                "Registered clips do not cover the narration duration; add licensed still "
                "images or longer video clips instead of looping footage."
            )
        target_frames = math.ceil(
            max(min_still_frames, min(max_still_frames, frames_remaining / len(image_records)))
        )
        frames_left = frames_remaining
        cursor = 0
        while frames_left > 0:
            take = min(target_frames, frames_left)
            image_segments.append((image_records[cursor % len(image_records)], take))
            frames_left -= take
            cursor += 1
    # The first map/stock scene opens the film (cold-open zoom); remaining
    # scenes book-end the piece inside the closing stretch of the timeline,
    # where comparison content typically plays in this genre.
    closing_start = 0.70
    timeline: list[tuple[dict[str, object], int]] = []
    if video_segments:
        timeline.append(video_segments[0])
    extras = video_segments[1:]
    anchors: dict[int, list[tuple[dict[str, object], int]]] = {}
    spread = len(extras) + 1
    for position, segment in enumerate(extras, start=1):
        fraction = closing_start + (1.0 - closing_start) * position / spread
        anchor = min(len(image_segments), round(len(image_segments) * fraction))
        anchors.setdefault(anchor, []).append(segment)
    for index, segment in enumerate(image_segments):
        timeline.extend(anchors.pop(index, []))
        timeline.append(segment)
    timeline.extend(anchors.pop(len(image_segments), []))
    for leftover in anchors.values():
        timeline.extend(leftover)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.mp4"
    )
    concat_inputs: list[str] = []
    filters: list[str] = []
    for index, (record, frame_count) in enumerate(timeline):
        segment_duration = frame_count / FRAME_RATE
        source = Path(str(record["path"]))
        if record.get("media_type") == "video":
            concat_inputs.extend(
                ["-t", f"{segment_duration:.6f}", "-i", str(source)]
            )
            filters.append(
                f"[{index}:v]scale={config.width}:{config.height}:"
                f"force_original_aspect_ratio=increase,crop={config.width}:{config.height},"
                f"fps={FRAME_RATE},trim=end_frame={frame_count},setpts=PTS-STARTPTS,"
                f"setsar=1,format=yuv420p[v{index}]"
            )
        else:
            concat_inputs.extend(
                [
                    "-loop", "1", "-framerate", str(FRAME_RATE),
                    "-t", f"{segment_duration:.6f}", "-i", str(source),
                ]
            )
            # Alternating Ken Burns motion per segment: push-in with drift,
            # pull-back, lateral pan, vertical pan — plus a restrained grade
            # (mild saturation/contrast lift and a soft vignette).
            motion_mode = index % 4
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
                    f"x='(iw-iw/zoom)*(on-1)/{max(1, frame_count)}':"
                    "y='ih/2-(ih/zoom/2)'"
                )
            else:
                motion = (
                    "zoompan=z=1.08:"
                    "x='iw/2-(iw/zoom/2)':"
                    f"y='(ih-ih/zoom)*(on-1)/{max(1, frame_count)}'"
                )
            filters.append(
                f"[{index}:v]"
                f"scale={config.width}:{config.height}:force_original_aspect_ratio=increase,"
                f"crop={config.width}:{config.height},"
                f"{motion}:d=1:s={config.width}x{config.height}:fps={FRAME_RATE},"
                f"eq=saturation=1.05:contrast=1.03,vignette=angle=PI/6,"
                f"trim=end_frame={frame_count},setpts=PTS-STARTPTS,setsar=1,"
                f"format=yuv420p[v{index}]"
            )
    narration_index = len(timeline)
    concat_inputs.extend(["-i", str(narration)])
    music_index: int | None = None
    if music_records:
        music_index = narration_index + 1
        concat_inputs.extend(["-stream_loop", "-1", "-i", str(music_records[0]["path"])])
    subtitle_index = narration_index + 1 + int(music_index is not None)
    concat_inputs.extend(["-i", str(subtitles)])
    joined = "".join(f"[v{index}]" for index in range(len(timeline)))
    filters.append(f"{joined}concat=n={len(timeline)}:v=1:a=0[vout]")
    if music_index is not None:
        filters.extend(
            [
                f"[{narration_index}:a:0]volume=1.0[narration]",
                f"[{music_index}:a:0]volume=0.1[music]",
                "[narration][music]amix=inputs=2:duration=first:dropout_transition=2,"
                "alimiter=limit=0.95[aout]",
            ]
        )
    command = [
        ffmpeg, "-y", "-v", "error",
        "-filter_complex_threads", "1",
        *concat_inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]",
        "-map", "[aout]" if music_index is not None else f"{narration_index}:a:0",
        "-map", f"{subtitle_index}:0",
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
            raise RenderError(
                f"FFmpeg render failed ({result.returncode}): {result.stderr[-3000:]}"
            )
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise RenderError("FFmpeg completed without producing a video file.")
        probe_video(config, temporary_output)
        temporary_output.replace(destination)
    except subprocess.TimeoutExpired as exc:
        temporary_output.unlink(missing_ok=True)
        raise RenderError("FFmpeg render exceeded its two-hour timeout.") from exc
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise
    return destination


def probe_video(config: FactoryConfig, path: Path) -> dict[str, object]:
    ffprobe = shutil.which(config.ffprobe)
    if not ffprobe:
        raise RenderError(f"FFprobe executable not found: {config.ffprobe}")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode:
        raise RenderError(f"FFprobe failed: {result.stderr[-1000:]}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RenderError("FFprobe returned invalid JSON.") from exc
    if not isinstance(parsed, dict) or not parsed.get("streams"):
        raise RenderError("FFprobe found no media streams.")
    return parsed
