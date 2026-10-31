"""Create a high-contrast 1280x720 JPEG thumbnail using FFmpeg."""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path

from geofactory.core.config import FactoryConfig

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720
MAX_TITLE_CHARS = 48


def _escape_filter_path(path: Path) -> str:
    value = str(path.resolve())
    return "".join(f"\\{character}" if character in "\\':,[];" else character for character in value)


def _find_bold_font() -> Path:
    fc_match = shutil.which("fc-match")
    if fc_match:
        result = subprocess.run(
            [fc_match, "-f", "%{file}", "DejaVu Sans:style=Bold"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            path = Path(result.stdout)
            if path.is_file():
                return path
    for candidate in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ):
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "No supported bold font was found. Install DejaVu Sans or Arial for FFmpeg drawtext."
    )


def make_thumbnail(
    topic: str,
    short_text: str,
    destination: Path,
    config: FactoryConfig,
    background: Path | None = None,
) -> Path:
    """Create an original title-card JPEG, optionally over a rights-cleared photograph."""
    title = " ".join(short_text.split()).strip()
    if not title:
        raise ValueError("Thumbnail title text cannot be empty.")
    if len(title) > MAX_TITLE_CHARS:
        raise ValueError(f"Thumbnail text must be {MAX_TITLE_CHARS} characters or fewer.")
    if background is not None:
        background = background.resolve(strict=True)
        if not background.is_file():
            raise ValueError(f"Thumbnail background is not a regular file: {background}")

    svg_path = destination.with_suffix(".svg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{THUMBNAIL_WIDTH}" height="{THUMBNAIL_HEIGHT}" viewBox="0 0 {THUMBNAIL_WIDTH} {THUMBNAIL_HEIGHT}">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#10212d"/><stop offset="1" stop-color="#246f73"/></linearGradient></defs>
<rect width="1280" height="720" fill="url(#bg)"/>
<circle cx="1000" cy="270" r="220" fill="#e1ad4b" opacity=".92"/>
<path d="M770 425 Q1000 80 1210 425 Q1030 535 770 425" fill="#2f5660"/>
<text x="76" y="130" fill="#b9e2dd" font-family="Arial,sans-serif" font-size="26">GEOGRAPHY DOCUMENTARY</text>
<text x="76" y="330" fill="white" font-family="Arial,sans-serif" font-size="68" font-weight="700">{html.escape(title)}</text>
<text x="76" y="625" fill="#d6e5e3" font-family="Arial,sans-serif" font-size="25">{html.escape(topic[:70])}</text>
</svg>"""
    svg_path.write_text(svg, encoding="utf-8")
    executable = shutil.which(config.ffmpeg)
    if not executable:
        return svg_path

    title_file = destination.with_name(f".{destination.stem}.{uuid.uuid4().hex}.txt")
    temporary_output = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.jpg"
    )
    wrapped_title = "\n".join(textwrap.wrap(title, width=22, break_long_words=False))
    if len(wrapped_title.splitlines()) > 2:
        raise ValueError("Thumbnail title must fit on no more than two lines.")
    title_file.write_text(wrapped_title, encoding="utf-8")
    try:
        font = _escape_filter_path(_find_bold_font())
        text_path = _escape_filter_path(title_file)
        source = background or svg_path
        filters = (
            f"scale={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT},setsar=1,"
            "drawbox=x=0:y=400:w=iw:h=320:color=black@0.72:t=fill,"
            f"drawtext=fontfile={font}:textfile={text_path}:"
            "fontcolor=white:fontsize=74:line_spacing=12:"
            "x=64:y=470:shadowcolor=black@0.9:shadowx=3:shadowy=3"
        )
        result = subprocess.run(
            [
                executable, "-y", "-v", "error", "-i", str(source),
                "-vf", filters, "-frames:v", "1", "-q:v", "2",
                "-f", "image2", str(temporary_output),
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"FFmpeg thumbnail generation failed ({result.returncode}): "
                f"{result.stderr[-1500:]}"
            )
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise RuntimeError("FFmpeg did not create a non-empty JPEG thumbnail.")
        probe = subprocess.run(
            [
                shutil.which(config.ffprobe) or config.ffprobe, "-v", "error",
                "-select_streams", "v:0", "-show_entries",
                "stream=codec_name,width,height", "-of", "json",
                str(temporary_output),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if probe.returncode:
            raise RuntimeError(f"FFprobe could not validate the thumbnail: {probe.stderr[-1000:]}")
        try:
            stream = json.loads(probe.stdout)["streams"][0]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("FFprobe returned invalid thumbnail metadata.") from exc
        if (
            stream.get("codec_name") != "mjpeg"
            or stream.get("width") != THUMBNAIL_WIDTH
            or stream.get("height") != THUMBNAIL_HEIGHT
        ):
            raise RuntimeError("Thumbnail must be an FFprobe-readable 1280x720 JPEG.")
        temporary_output.replace(destination)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise
    finally:
        title_file.unlink(missing_ok=True)
    return destination
