"""Memory-bounded Natural Earth country-map frames and FFmpeg scene segments."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

DATASET_NAME = "Natural Earth 1:110m Admin 0 Countries"
DATASET_VERSION = "5.1.1"
DATASET_LICENSE = "Public Domain"
DATASET_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.1/geojson/ne_110m_admin_0_countries.geojson"
)
DATASET_LICENSE_URL = "https://www.naturalearthdata.com/about/terms-of-use/"
MAX_DATASET_BYTES = 20 * 1024 * 1024
QUALIFICATION = "Boundaries follow Natural Earth de facto depiction; disputed status may differ."


class MapAnimationError(RuntimeError):
    """Raised when map data or scene rendering cannot be verified."""


@dataclass(frozen=True)
class MapMarker:
    longitude: float
    latitude: float
    label: str
    source: str = ""


@dataclass(frozen=True)
class MapSceneSpec:
    country_iso_a3: str
    duration_seconds: float = 10.0
    title: str = ""
    route: tuple[tuple[float, float], ...] = ()
    route_source: str = ""
    markers: tuple[MapMarker, ...] = ()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_paths(root: Path) -> tuple[Path, Path]:
    directory = root / "data" / "natural-earth"
    return (
        directory / "ne_110m_admin_0_countries.geojson",
        directory / "dataset.json",
    )


def _download_dataset(destination: Path, manifest_path: Path) -> dict[str, Any]:
    parsed = urlparse(DATASET_URL)
    if parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com":
        raise MapAnimationError("Natural Earth download URL is not the approved HTTPS host.")
    request = Request(DATASET_URL, headers={"User-Agent": "GeoFactory/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            final_url = urlparse(response.geturl())
            if final_url.scheme != "https" or final_url.hostname != parsed.hostname:
                raise MapAnimationError("Natural Earth download redirected to an unapproved host.")
            body = response.read(MAX_DATASET_BYTES + 1)
            if len(body) > MAX_DATASET_BYTES:
                raise MapAnimationError("Natural Earth country dataset exceeds 20 MiB.")
    except HTTPError as exc:
        raise MapAnimationError(
            f"Natural Earth data download returned HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise MapAnimationError(
            f"Natural Earth data download failed ({type(exc).__name__})."
        ) from exc
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MapAnimationError("Natural Earth response is not valid UTF-8 GeoJSON.") from exc
    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or data.get("name") != "ne_110m_admin_0_countries"
        or not isinstance(data.get("features"), list)
        or not data["features"]
    ):
        raise MapAnimationError("Downloaded file is not the expected Natural Earth dataset.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=".natural-earth-", suffix=".tmp",
        dir=destination.parent, delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(destination)
    now = datetime.now(timezone.utc)
    manifest = {
        "dataset_name": DATASET_NAME,
        "dataset_version": DATASET_VERSION,
        "licence": DATASET_LICENSE,
        "licence_url": DATASET_LICENSE_URL,
        "dataset_url": DATASET_URL,
        "download_date": now.date().isoformat(),
        "downloaded_at": now.isoformat(),
        "sha256": _sha256(destination),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_natural_earth(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load verified cached data, downloading the pinned public-domain release as needed."""
    data_path, manifest_path = dataset_paths(root)
    manifest: dict[str, Any] | None = None
    if data_path.is_file() and manifest_path.is_file():
        try:
            parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                isinstance(parsed, dict)
                and parsed.get("dataset_name") == DATASET_NAME
                and parsed.get("dataset_version") == DATASET_VERSION
                and parsed.get("licence") == DATASET_LICENSE
                and parsed.get("licence_url") == DATASET_LICENSE_URL
                and parsed.get("dataset_url") == DATASET_URL
                and parsed.get("sha256") == _sha256(data_path)
            ):
                manifest = parsed
        except (OSError, json.JSONDecodeError):
            manifest = None
    if manifest is None:
        manifest = _download_dataset(data_path, manifest_path)
    try:
        collection = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MapAnimationError(f"Cached Natural Earth GeoJSON is unreadable: {exc}") from exc
    if (
        not isinstance(collection, dict)
        or collection.get("type") != "FeatureCollection"
        or not isinstance(collection.get("features"), list)
    ):
        raise MapAnimationError("Cached Natural Earth data is not a GeoJSON FeatureCollection.")
    return collection, manifest


def _feature_code(feature: dict[str, Any]) -> str:
    properties = feature.get("properties", {})
    if not isinstance(properties, dict):
        return ""
    code = properties.get("ISO_A3_EH") or properties.get("ADM0_A3")
    return str(code).upper() if isinstance(code, str) else ""


def _feature_name(feature: dict[str, Any]) -> str:
    properties = feature.get("properties", {})
    if not isinstance(properties, dict):
        return ""
    return str(properties.get("ADMIN") or properties.get("NAME") or "")


def _polygons(feature: dict[str, Any]) -> list[list[list[tuple[float, float]]]]:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        return []
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        source = [coordinates]
    elif kind == "MultiPolygon":
        source = coordinates
    else:
        return []
    polygons: list[list[list[tuple[float, float]]]] = []
    if not isinstance(source, list):
        return polygons
    for polygon in source:
        if not isinstance(polygon, list) or not polygon:
            continue
        rings: list[list[tuple[float, float]]] = []
        for ring in polygon:
            if not isinstance(ring, list):
                continue
            points: list[tuple[float, float]] = []
            for point in ring:
                if (
                    isinstance(point, (list, tuple))
                    and len(point) >= 2
                    and isinstance(point[0], (int, float))
                    and isinstance(point[1], (int, float))
                    and math.isfinite(float(point[0]))
                    and math.isfinite(float(point[1]))
                ):
                    points.append((float(point[0]), float(point[1])))
            if len(points) >= 3:
                rings.append(points)
        if rings:
            polygons.append(rings)
    return polygons


def find_country(collection: dict[str, Any], iso_a3: str) -> dict[str, Any]:
    code = iso_a3.strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise MapAnimationError("Country must be identified by a three-letter ISO A3 code.")
    for feature in collection["features"]:
        if isinstance(feature, dict) and _feature_code(feature) == code:
            if not _polygons(feature):
                break
            return feature
    raise MapAnimationError(f"Natural Earth has no country feature for ISO A3 {code}.")


def _bounds(feature: dict[str, Any]) -> tuple[float, float, float, float]:
    points = [
        point
        for polygon in _polygons(feature)
        for ring in polygon[:1]
        for point in ring
    ]
    if not points:
        raise MapAnimationError("Country feature has no polygon coordinates.")
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def _coordinates_to_pixels(
    point: tuple[float, float],
    view: tuple[float, float, float, float],
    width: int,
    height: int,
) -> tuple[int, int]:
    left, bottom, right, top = view
    span_x = max(1e-6, right - left)
    span_y = max(1e-6, top - bottom)
    x = round((point[0] - left) * (width - 1) / span_x)
    y = round((top - point[1]) * (height - 1) / span_y)
    return x, y


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: tuple[int, int, int],
    width: int,
) -> None:
    if len(points) < 2:
        return
    draw.line(points, fill=(8, 18, 30), width=width + 7, joint="curve")
    draw.line(points, fill=fill, width=width, joint="curve")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    angle = math.atan2(y2 - y1, x2 - x1)
    length = max(14, width * 2)
    wing_a = (
        round(x2 - length * math.cos(angle - 0.55)),
        round(y2 - length * math.sin(angle - 0.55)),
    )
    wing_b = (
        round(x2 - length * math.cos(angle + 0.55)),
        round(y2 - length * math.sin(angle + 0.55)),
    )
    draw.polygon([points[-1], wing_a, wing_b], fill=fill)
    draw.line([points[-1], wing_a], fill=(8, 18, 30), width=max(2, width // 3))
    draw.line([points[-1], wing_b], fill=(8, 18, 30), width=max(2, width // 3))


def _draw_frame(
    collection: dict[str, Any],
    target: dict[str, Any],
    spec: MapSceneSpec,
    frame_index: int,
    frame_count: int,
    width: int,
    height: int,
) -> Image.Image:
    progress = frame_index / max(1, frame_count - 1)
    eased = progress * progress * (3 - 2 * progress)
    min_x, min_y, max_x, max_y = _bounds(target)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    focus_width = max(12.0, (max_x - min_x) * 1.35)
    world_width = 360.0
    view_width = world_width * (1 - eased) + focus_width * eased
    view_height = view_width * height / width
    center_view_x = center_x * eased
    center_view_y = center_y * eased
    view = (
        center_view_x - view_width / 2,
        center_view_y - view_height / 2,
        center_view_x + view_width / 2,
        center_view_y + view_height / 2,
    )
    image = Image.new("RGB", (width, height), (11, 45, 70))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(22, 107, 133), width=4)
    for feature in collection["features"]:
        if not isinstance(feature, dict):
            continue
        highlighted = _feature_code(feature) == spec.country_iso_a3.upper()
        land = (218, 183, 118) if highlighted else (91, 112, 103)
        border = (255, 232, 183) if highlighted else (23, 45, 49)
        for polygon in _polygons(feature):
            exterior = polygon[0]
            pixel_points = [
                _coordinates_to_pixels(point, view, width, height)
                for point in exterior
            ]
            if len(pixel_points) >= 3:
                draw.polygon(pixel_points, fill=land)
                for interior in polygon[1:]:
                    hole = [
                        _coordinates_to_pixels(point, view, width, height)
                        for point in interior
                    ]
                    if len(hole) >= 3:
                        draw.polygon(hole, fill=(11, 45, 70))
                draw.line(pixel_points + [pixel_points[0]], fill=border, width=2)
    if spec.route:
        route_points = [
            _coordinates_to_pixels(point, view, width, height) for point in spec.route
        ]
        _draw_arrow(draw, route_points, (255, 213, 67), max(5, width // 150))
    for marker in spec.markers:
        x, y = _coordinates_to_pixels(
            (marker.longitude, marker.latitude), view, width, height
        )
        radius = max(7, width // 100)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(237, 49, 48),
            outline=(255, 255, 255),
            width=3,
        )
        if marker.label:
            draw.text((x + radius + 5, y - radius), marker.label, fill="white")
    title = spec.title or _feature_name(target)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(24, width // 28))
        small_font = ImageFont.truetype("DejaVuSans.ttf", max(12, width // 90))
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    draw.rounded_rectangle(
        (24, 20, min(width - 24, 24 + max(300, len(title) * width // 45)), 78),
        radius=12,
        fill=(4, 17, 26),
    )
    draw.text((42, 30), title[:48], font=font, fill=(255, 255, 255))
    draw.rectangle((0, height - 40, width, height), fill=(4, 17, 26))
    draw.text((18, height - 30), QUALIFICATION, font=small_font, fill=(255, 236, 191))
    return image


def create_map_scene(
    root: Path,
    destination: Path,
    spec: MapSceneSpec,
    *,
    ffmpeg_name: str = "ffmpeg",
    width: int = 1280,
    height: int = 720,
    fps: int = 15,
) -> dict[str, Any]:
    """Render a world-to-country zoom and highlight to PNG frames and an MP4 segment."""
    if not re.fullmatch(r"[A-Za-z]{3}", spec.country_iso_a3):
        raise MapAnimationError("Country must be identified by a three-letter ISO A3 code.")
    if not 2 <= spec.duration_seconds <= 120:
        raise MapAnimationError("Map scene duration must be between 2 and 120 seconds.")
    if width < 320 or height < 180 or width % 2 or height % 2:
        raise MapAnimationError("Map scene dimensions must be even and at least 320x180.")
    if not 1 <= fps <= 30:
        raise MapAnimationError("Map scene frame rate must be between 1 and 30 fps.")
    collection, dataset_manifest = load_natural_earth(root)
    target = find_country(collection, spec.country_iso_a3)
    for longitude, latitude in spec.route:
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise MapAnimationError("Route coordinates must be longitude/latitude pairs.")
    if spec.route and (len(spec.route) < 2 or not spec.route_source.strip()):
        raise MapAnimationError(
            "A route needs at least two coordinates and a recorded source; routes are never inferred."
        )
    for marker in spec.markers:
        if (
            not -180 <= marker.longitude <= 180
            or not -90 <= marker.latitude <= 90
            or len(marker.label) > 60
            or not marker.source.strip()
        ):
            raise MapAnimationError(
                "Map markers need valid coordinates, a short label, and a recorded source."
            )
    ffmpeg = shutil.which(ffmpeg_name)
    if not ffmpeg:
        raise MapAnimationError(f"FFmpeg executable not found: {ffmpeg_name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = destination.with_suffix(".frames")
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_count = math.ceil(spec.duration_seconds * fps)
    for index in range(frame_count):
        frame = _draw_frame(collection, target, spec, index, frame_count, width, height)
        frame.save(frames_dir / f"frame-{index:05d}.png", optimize=True)
    temporary_output = destination.with_name(
        f".{destination.stem}.rendering.tmp.mp4"
    )
    try:
        result = subprocess.run(
            [
                ffmpeg, "-y", "-v", "error", "-framerate", str(fps),
                "-i", str(frames_dir / "frame-%05d.png"),
                "-frames:v", str(frame_count), "-an",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(temporary_output),
            ],
            capture_output=True,
            text=True,
            timeout=max(180, int(spec.duration_seconds * 30)),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        temporary_output.unlink(missing_ok=True)
        raise MapAnimationError(
            f"FFmpeg map segment conversion failed ({type(exc).__name__})."
        ) from exc
    if result.returncode or not temporary_output.is_file():
        temporary_output.unlink(missing_ok=True)
        raise MapAnimationError(
            f"FFmpeg map segment conversion failed: {result.stderr[-1000:]}"
        )
    temporary_output.replace(destination)
    scene_details = asdict(spec)
    scene_details["country_iso_a3"] = spec.country_iso_a3.upper()
    manifest = {
        "scene": scene_details,
        "country_name": _feature_name(target),
        "dataset_name": dataset_manifest["dataset_name"],
        "dataset_version": dataset_manifest["dataset_version"],
        "licence": dataset_manifest["licence"],
        "licence_url": dataset_manifest["licence_url"],
        "dataset_download_date": dataset_manifest["download_date"],
        "dataset_sha256": dataset_manifest["sha256"],
        "segment_sha256": _sha256(destination),
        "width": width,
        "height": height,
        "fps": fps,
        "frames": frame_count,
        "qualification": QUALIFICATION,
        "route_source": spec.route_source,
        "marker_sources": [marker.source for marker in spec.markers],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    destination.with_suffix(".map.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def validate_map_scene(path: Path) -> dict[str, Any]:
    """Verify a rendered map clip has an intact sidecar and an identified licensed dataset."""
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".mp4":
        raise MapAnimationError("Map scene must be a regular, non-symlink MP4 file.")
    sidecar_path = path.with_suffix(".map.json")
    if sidecar_path.is_symlink() or not sidecar_path.is_file():
        raise MapAnimationError("Map scene metadata must be a regular, non-symlink file.")
    try:
        manifest = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MapAnimationError(f"Map scene metadata is missing or invalid: {exc}") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("dataset_name") != DATASET_NAME
        or manifest.get("dataset_version") != DATASET_VERSION
        or manifest.get("licence") != DATASET_LICENSE
        or manifest.get("licence_url") != DATASET_LICENSE_URL
        or manifest.get("segment_sha256") != _sha256(path)
        or not isinstance(manifest.get("dataset_sha256"), str)
        or len(manifest["dataset_sha256"]) != 64
        or not re.fullmatch(r"[0-9a-f]{64}", manifest["dataset_sha256"])
        or not isinstance(manifest.get("scene"), dict)
        or not re.fullmatch(
            r"[A-Z]{3}",
            str(manifest.get("scene", {}).get("country_iso_a3", "")),
        )
    ):
        raise MapAnimationError("Map scene dataset metadata or segment hash is invalid.")
    try:
        date.fromisoformat(str(manifest["dataset_download_date"]))
    except (KeyError, ValueError) as exc:
        raise MapAnimationError("Map scene has no valid Natural Earth download date.") from exc
    return manifest
