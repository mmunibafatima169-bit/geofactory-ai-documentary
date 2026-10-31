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
    if not images:
        raise RenderError("At least one rights-cleared visual asset is required.")
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
    if not video_records and not image_records:
        raise RenderError("At least one licensed video clip or still image is required.")
    video_durations: list[tuple[dict[str, object], float]] = []
    if video_records:
        for record in video_records:
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
    timeline: list[tuple[dict[str, object], int]] = []
    frames_remaining = total_frames
    for record, clip_duration in video_durations:
        frame_count = min(math.ceil(clip_duration * FRAME_RATE), frames_remaining)
        if frame_count > 0:
            timeline.append((record, frame_count))
            frames_remaining -= frame_count
        if frames_remaining == 0:
            break
    if frames_remaining:
        if not image_records:
            raise RenderError(
                "Registered clips do not cover the narration duration; add licensed still "
                "images or longer video clips instead of looping footage."
            )
        base_frames = frames_remaining // len(image_records)
        image_frames = [base_frames] * len(image_records)
        for index in range(frames_remaining % len(image_records)):
            image_frames[index] += 1
        timeline.extend(
            (record, frame_count)
            for record, frame_count in zip(image_records, image_frames, strict=True)
            if frame_count > 0
        )
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
            filters.append(
                f"[{index}:v]"
                f"scale={config.width}:{config.height}:force_original_aspect_ratio=increase,"
                f"crop={config.width}:{config.height},"
                f"zoompan=z='min(zoom+0.00006,1.08)':"
                f"x='iw/2-(iw/zoom/2)+sin(on/250)*8':"
                f"y='ih/2-(ih/zoom/2)+cos(on/300)*5':"
                f"d=1:s={config.width}x{config.height}:fps={FRAME_RATE},"
                f"trim=end_frame={frame_count},setpts=PTS-STARTPTS,"
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
