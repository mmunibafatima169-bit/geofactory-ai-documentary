"""Memory-bounded FFmpeg Ken Burns rendering with soft subtitles and narration sync."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from pathlib import Path

from geofactory.core.config import FactoryConfig
from geofactory.media.asset_manager import ALLOWED_LICENSES, sha256_file
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
    resolved_images = []
    for image in images:
        resolved = image.resolve(strict=True)
        record = records_by_path.get(str(resolved))
        if record is None or record.get("licence") not in ALLOWED_LICENSES:
            raise RenderError(f"Visual is not registered with an accepted licence: {image}")
        if (
            not record.get("commercial_use")
            or not str(record.get("attribution", "")).strip()
            or sha256_file(resolved) != record.get("file_sha256")
        ):
            raise RenderError(f"Visual rights or file hash validation failed: {image}")
        resolved_images.append(resolved)

    duration = audio_duration_seconds(narration, config.ffprobe)
    if duration <= 0:
        raise RenderError("Narration duration is not positive.")
    total_frames = max(1, math.ceil(duration * FRAME_RATE))
    frames_per_image = [total_frames // len(images)] * len(images)
    for index in range(total_frames % len(images)):
        frames_per_image[index] += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.mp4"
    )
    concat_inputs: list[str] = []
    filters: list[str] = []
    for index, (image, frame_count) in enumerate(
        zip(resolved_images, frames_per_image, strict=True)
    ):
        segment_duration = frame_count / FRAME_RATE
        concat_inputs.extend(
            [
                "-loop", "1",
                "-framerate", str(FRAME_RATE),
                "-t", f"{segment_duration:.6f}",
                "-i", str(image),
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
    audio_index = len(resolved_images)
    subtitle_index = audio_index + 1
    concat_inputs.extend(["-i", str(narration), "-i", str(subtitles)])
    joined = "".join(f"[v{index}]" for index in range(len(images)))
    filters.append(f"{joined}concat=n={len(images)}:v=1:a=0[vout]")
    command = [
        ffmpeg, "-y", "-v", "error",
        "-filter_complex_threads", "1",
        *concat_inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", f"{audio_index}:a:0",
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
