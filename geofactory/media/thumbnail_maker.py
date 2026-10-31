"""Create a high-contrast 1280x720 JPEG thumbnail using Pillow."""

from __future__ import annotations

import html
import shutil
import subprocess
import uuid
from pathlib import Path

from geofactory.core.config import FactoryConfig

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720
MAX_TITLE_CHARS = 48


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
        "No supported bold font was found. Install DejaVu Sans or Arial for thumbnail text."
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
    temporary_output = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.jpg"
    )
    poster_path: Path | None = None
    try:
        from PIL import Image, ImageDraw, ImageFont

        if background:
            image_source = background
            if background.suffix.lower() == ".mp4":
                ffmpeg = shutil.which(config.ffmpeg)
                if not ffmpeg:
                    raise RuntimeError("FFmpeg is required to extract a thumbnail from video.")
                poster_path = destination.with_name(
                    f".{destination.stem}.{uuid.uuid4().hex}.poster.png"
                )
                result = subprocess.run(
                    [
                        ffmpeg, "-y", "-v", "error", "-ss", "1",
                        "-i", str(background), "-frames:v", "1", str(poster_path),
                    ],
                    capture_output=True, text=True, timeout=60, check=False,
                )
                if result.returncode or not poster_path.is_file():
                    raise RuntimeError(
                        f"FFmpeg could not extract a video thumbnail frame: {result.stderr[-1000:]}"
                    )
                image_source = poster_path
            with Image.open(image_source) as opened:
                image = opened.convert("RGB")
            source_ratio = image.width / image.height
            target_ratio = THUMBNAIL_WIDTH / THUMBNAIL_HEIGHT
            if source_ratio > target_ratio:
                new_width = round(image.height * target_ratio)
                left = (image.width - new_width) // 2
                image = image.crop((left, 0, left + new_width, image.height))
            else:
                new_height = round(image.width / target_ratio)
                top = (image.height - new_height) // 2
                image = image.crop((0, top, image.width, top + new_height))
            image = image.resize(
                (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS
            )
        else:
            image = Image.new("RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT))
            pixels = image.load()
            for y in range(THUMBNAIL_HEIGHT):
                ratio = y / (THUMBNAIL_HEIGHT - 1)
                color = (
                    round(16 + 20 * ratio),
                    round(33 + 85 * ratio),
                    round(45 + 60 * ratio),
                )
                for x in range(THUMBNAIL_WIDTH):
                    pixels[x, y] = color

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        for y in range(360, THUMBNAIL_HEIGHT):
            alpha = round(205 * ((y - 360) / (THUMBNAIL_HEIGHT - 360)))
            overlay_draw.line((0, y, THUMBNAIL_WIDTH, y), fill=(5, 12, 18, alpha))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

        font_path = _find_bold_font()
        draw = ImageDraw.Draw(image)
        words = title.split()
        wrapped_title: list[str] | None = None
        font: ImageFont.FreeTypeFont | None = None
        font_size = 82
        while font_size >= 36:
            font = ImageFont.truetype(str(font_path), font_size)
            full_width = draw.textbbox((0, 0), title, font=font, stroke_width=2)[2]
            if full_width <= 1150:
                wrapped_title = [title]
                break
            candidates: list[tuple[int, int, list[str]]] = []
            for split in range(1, len(words)):
                lines = [" ".join(words[:split]), " ".join(words[split:])]
                widths = [
                    draw.textbbox((0, 0), line, font=font, stroke_width=2)[2]
                    for line in lines
                ]
                if max(widths) <= 1150:
                    candidates.append((max(widths), abs(widths[0] - widths[1]), lines))
            if candidates:
                wrapped_title = min(candidates, key=lambda item: (item[0], item[1]))[2]
                break
            font_size -= 2
        if wrapped_title is None or font is None:
            raise ValueError("Thumbnail title cannot fit legibly at 1280x720.")
        line_height = font_size + 16
        block_height = line_height * len(wrapped_title)
        y = 665 - block_height
        for line in wrapped_title:
            draw.text(
                (64, y), line, font=font, fill="white",
                stroke_width=3, stroke_fill=(0, 0, 0),
            )
            y += line_height
        image.save(temporary_output, format="JPEG", quality=94, optimize=True)
        with Image.open(temporary_output) as verification:
            if verification.format != "JPEG" or verification.size != (
                THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT
            ):
                raise RuntimeError("Pillow did not create a valid 1280x720 JPEG thumbnail.")
        temporary_output.replace(destination)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise
    finally:
        if poster_path:
            poster_path.unlink(missing_ok=True)
    return destination
