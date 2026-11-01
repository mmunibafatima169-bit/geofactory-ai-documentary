"""Generate distinct, map-first thumbnail concepts with editable JSON recipes."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

from geofactory.media.map_animation_engine import (
    _bounds,
    _coordinates_to_pixels,
    _feature_code,
    _polygons,
    find_country,
    load_natural_earth,
)
from geofactory.media.thumbnail_maker import (
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDTH,
    _find_bold_font,
)

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "behind", "by", "can", "does", "for",
    "from", "how", "in", "is", "it", "of", "on", "or", "the", "to", "what",
    "when", "where", "why", "with",
}

MASTER_WIDTH = 1920
MASTER_HEIGHT = 1080
RENDER_SCALE = MASTER_WIDTH / THUMBNAIL_WIDTH
SUPERSAMPLE_FACTOR = 2
REFERENCE_SATURATION_MEDIAN = 0.5194
REFERENCE_SATURATION_RANGE = (0.3361, 0.7028)
REFERENCE_HEADLINE_COVERAGE_MEDIAN = 0.067
REFERENCE_HEADLINE_COVERAGE_RANGE = (0.0, 0.2382)

CONCEPTS: tuple[dict[str, Any], ...] = (
    {
        "id": "coastal-signal",
        "palette": {
            "ocean": (8, 42, 59), "land": (132, 112, 82),
            "highlight": (241, 53, 47), "arrow": (248, 249, 242),
            "accent": (242, 53, 47),
        },
        "zoom": 1.7,
        "headline_anchor": (56, 410),
        "arrow_style": "curved-pointer",
        "map_anchor": "center",
    },
    {
        "id": "terrain-route",
        "palette": {
            "ocean": (30, 95, 116), "land": (181, 142, 99),
            "highlight": (47, 193, 95), "arrow": (255, 255, 248),
            "accent": (255, 207, 45),
        },
        "zoom": 2.15,
        "headline_anchor": (62, 92),
        "arrow_style": "diagonal-pointer",
        "map_anchor": "right",
    },
    {
        "id": "midnight-relief",
        "palette": {
            "ocean": (4, 25, 53), "land": (71, 88, 98),
            "highlight": (250, 203, 40), "arrow": (247, 66, 49),
            "accent": (247, 66, 49),
        },
        "zoom": 1.9,
        "headline_anchor": (72, 112),
        "arrow_style": "straight-pointer",
        "map_anchor": "left",
    },
)


class ThumbnailEngineError(RuntimeError):
    """Raised when thumbnail concepts cannot be generated or verified."""


def _headline_for(topic: str, headline: str | None) -> str:
    if headline:
        words = headline.strip().split()
    else:
        tokens = re.findall(r"[A-Za-z0-9'-]+", topic)
        words = [
            token for token in tokens
            if token.casefold() not in STOP_WORDS and len(token) > 1
        ][:4]
    if not 2 <= len(words) <= 5:
        raise ThumbnailEngineError(
            "Thumbnail headline must contain 2-5 words; supply a concise original headline."
        )
    return " ".join(words).upper()


def _font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path), size=size)


def _country_view(
    feature: dict[str, Any], width: int, height: int, zoom: float
) -> tuple[float, float, float, float]:
    left, bottom, right, top = _bounds(feature)
    center_x, center_y = (left + right) / 2, (bottom + top) / 2
    span_x = max(4.0, (right - left) * zoom)
    span_y = max(4.0, (top - bottom) * zoom)
    desired_y = span_x * height / width
    span_y = max(span_y, desired_y)
    span_x = span_y * width / height
    return (
        center_x - span_x / 2, center_y - span_y / 2,
        center_x + span_x / 2, center_y + span_y / 2,
    )


def _draw_map(
    image: Image.Image,
    collection: dict[str, Any],
    target: dict[str, Any],
    palette: dict[str, tuple[int, int, int]],
    zoom: float,
    anchor: str,
    scale: float,
) -> tuple[int, int]:
    width, height = image.size
    draw = ImageDraw.Draw(image)
    view = _country_view(target, width, height, zoom)
    target_center_x = sum((_bounds(target)[0], _bounds(target)[2])) / 2
    target_center_y = sum((_bounds(target)[1], _bounds(target)[3])) / 2
    if anchor == "right":
        shift = width * 0.1
    elif anchor == "left":
        shift = -width * 0.08
    else:
        shift = 0
    view = (view[0] - shift * (view[2] - view[0]) / width,
            view[1], view[2] - shift * (view[2] - view[0]) / width, view[3])
    target_pixel = _coordinates_to_pixels(
        (target_center_x, target_center_y), view, width, height
    )
    for feature in collection["features"]:
        if not isinstance(feature, dict):
            continue
        highlighted = _feature_code(feature) == _feature_code(target)
        fill = palette["highlight"] if highlighted else palette["land"]
        outline = (255, 247, 224) if highlighted else (34, 41, 47)
        for polygon in _polygons(feature):
            points = [
                _coordinates_to_pixels(point, view, width, height)
                for point in polygon[0]
            ]
            if len(points) >= 3:
                draw.polygon(points, fill=fill)
                for interior in polygon[1:]:
                    hole = [
                        _coordinates_to_pixels(point, view, width, height)
                        for point in interior
                    ]
                    if len(hole) >= 3:
                        draw.polygon(hole, fill=palette["ocean"])
                draw.line(
                    points + [points[0]], fill=outline,
                    width=round((3 if highlighted else 2) * scale),
                )
    return target_pixel


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    style: str,
    scale: float,
) -> None:
    x1, y1 = start
    x2, y2 = end
    if style == "curved-pointer":
        points = [
            (x1, y1),
            (round((x1 + x2) * 0.55), round(y1 - 65 * scale)),
            (x2, y2),
        ]
    elif style == "diagonal-pointer":
        points = [(x1, y1), (round((x1 + x2) * 0.5), y1), (x2, y2)]
    else:
        points = [start, end]
    draw.line(points, fill=(0, 0, 0), width=round(22 * scale), joint="curve")
    draw.line(points, fill=color, width=round(13 * scale), joint="curve")
    a, b = points[-2], points[-1]
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    size = 38 * scale
    wings = [
        (round(b[0] - size * math.cos(angle - 0.5)),
         round(b[1] - size * math.sin(angle - 0.5))),
        (round(b[0] - size * math.cos(angle + 0.5)),
         round(b[1] - size * math.sin(angle + 0.5))),
    ]
    draw.polygon([b, *wings], fill=color)


def _contrast_ratio(foreground: tuple[int, int, int], background: tuple[int, int, int]) -> float:
    def luminance(rgb: tuple[int, int, int]) -> float:
        channels = []
        for value in rgb:
            channel = value / 255
            channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _score_concept(
    headline: str,
    topic: str,
    font_size: int,
    country_found: bool,
    scale: float,
    headline_block_coverage: float,
    saturation: float,
    arrow_count: int,
    layout_variety: bool,
    badge_area_clear: bool,
) -> dict[str, Any]:
    words = headline.split()
    normalized_font_size = font_size / scale
    readable = len(words) <= 5 and normalized_font_size >= 58
    style_checks = {
        "map_hero_present": True,
        "highlighted_region_present": country_found,
        "arrow_or_marker_present": arrow_count > 0,
        "reference_saturation_band": 0.30 <= saturation <= 0.75,
        "headline_block_coverage_in_visual_estimate_range": (
            0.02 <= headline_block_coverage <= 0.24
        ),
        "short_bold_text": 2 <= len(words) <= 5,
        "layout_variety_present": layout_variety,
        "bottom_right_duration_area_clear": badge_area_clear,
        "mobile_text_size_heuristic_pass": readable,
    }
    topic_terms = {
        word.casefold() for word in re.findall(r"[A-Za-z0-9'-]+", topic)
        if word.casefold() not in STOP_WORDS
    }
    headline_terms = {
        word.casefold() for word in re.findall(r"[A-Za-z0-9'-]+", headline)
    }
    relevance = 100 if not topic_terms else round(
        100 * len(topic_terms & headline_terms) / len(topic_terms)
    )
    contrast = _contrast_ratio((255, 255, 255), (4, 8, 14))
    scores = {
        "mobile_readability": 100 if readable else 55,
        "contrast": min(100, round(contrast * 10)),
        "text_size": min(100, round(normalized_font_size / 0.78)),
        "style_match": round(100 * sum(style_checks.values()) / len(style_checks)),
        "geographic_accuracy": 100 if country_found else 0,
        "title_relevance": relevance,
    }
    scores["overall"] = round(
        scores["mobile_readability"] * 0.20
        + scores["contrast"] * 0.15
        + scores["text_size"] * 0.10
        + scores["style_match"] * 0.20
        + scores["geographic_accuracy"] * 0.20
        + scores["title_relevance"] * 0.15
    )
    return {
        "scores": scores,
        "style_checks": style_checks,
        "measurements": {
            "palette_mean_saturation": round(saturation, 3),
            "headline_block_coverage_fraction": round(headline_block_coverage, 3),
            "headline_block_coverage_design_range": [0.02, 0.24],
            "reference_median_saturation": REFERENCE_SATURATION_MEDIAN,
            "reference_saturation_range": list(REFERENCE_SATURATION_RANGE),
            "reference_median_headline_bbox_area_fraction_visual_estimate": (
                REFERENCE_HEADLINE_COVERAGE_MEDIAN
            ),
            "reference_headline_bbox_area_fraction_visual_estimate_range": list(
                REFERENCE_HEADLINE_COVERAGE_RANGE
            ),
            "arrow_count": arrow_count,
            "reference_arrows_or_routes_visible_count_visual_estimate": 8,
            "reference_marker_or_highlight_visible_count_visual_estimate": 12,
            "reference_bottom_right_clear_count_visual_estimate": 12,
            "layout_variety_pass": layout_variety,
            "bottom_right_duration_area_clear": badge_area_clear,
        },
    }


def _render_concept(
    topic: str,
    headline: str,
    target: dict[str, Any],
    collection: dict[str, Any],
    concept: dict[str, Any],
    output_path: Path,
    font_path: Path,
    layout_variety: bool,
) -> tuple[dict[str, Any], int]:
    palette = concept["palette"]
    scale = RENDER_SCALE * SUPERSAMPLE_FACTOR
    width, height = MASTER_WIDTH * SUPERSAMPLE_FACTOR, MASTER_HEIGHT * SUPERSAMPLE_FACTOR
    image = Image.new("RGB", (width, height), palette["ocean"])
    target_point = _draw_map(
        image, collection, target, palette, concept["zoom"], concept["map_anchor"],
        scale,
    )
    draw = ImageDraw.Draw(image)
    _draw_arrow(
        draw,
        (width - round(140 * scale), round(180 * scale)),
        (max(round(380 * scale), min(width - round(220 * scale), target_point[0])),
         max(round(120 * scale), min(height - round(150 * scale), target_point[1]))),
        palette["arrow"],
        concept["arrow_style"],
        scale,
    )
    marker_radius = round(19 * scale)
    draw.ellipse(
        (
            target_point[0] - marker_radius, target_point[1] - marker_radius,
            target_point[0] + marker_radius, target_point[1] + marker_radius,
        ),
        fill=palette["accent"],
        outline=(255, 255, 255),
        width=round(5 * scale),
    )
    draw.ellipse(
        (width - round(136 * scale), round(176 * scale),
         width - round(112 * scale), round(200 * scale)),
        fill=(235, 45, 43),
        outline=(255, 255, 255),
        width=round(3 * scale),
    )
    mask = Image.new("L", (64, 36))
    mask_pixels = mask.load()
    for y in range(mask.height):
        for x in range(mask.width):
            edge = max(
                abs(x - mask.width / 2) / (mask.width / 2),
                abs(y - mask.height / 2) / (mask.height / 2),
            )
            bottom = max(0.0, (y / mask.height - 0.70) * 85)
            mask_pixels[x, y] = round(min(135, max(0, (edge - 0.35) * 145 + bottom)))
    mask = mask.resize(image.size, Image.Resampling.BILINEAR)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay.putalpha(mask)
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    words = headline.split()
    headline_size = round((94 if len(headline) < 20 else 78) * scale)
    font = _font(font_path, headline_size)
    lines = [" ".join(words[: max(1, (len(words) + 1) // 2)]),
             " ".join(words[max(1, (len(words) + 1) // 2):])]
    if not lines[1]:
        lines = [headline, ""]
    x, y = (round(value * scale) for value in concept["headline_anchor"])
    max_width = round((770 if concept["id"] != "terrain-route" else 690) * scale)
    headline_area = 0
    headline_boxes: list[tuple[int, int, int, int]] = []
    for line in lines:
        if not line:
            continue
        while draw.textbbox(
            (0, 0), line, font=font, stroke_width=round(5 * scale)
        )[2] > max_width:
            headline_size -= 2
            if headline_size < round(54 * scale):
                raise ThumbnailEngineError(
                    "Headline cannot fit legibly at 1920x1080."
                )
            font = _font(font_path, headline_size)
        box = draw.textbbox(
            (x, y), line, font=font, stroke_width=round(5 * scale)
        )
        headline_box = (
            box[0] - round(18 * scale), box[1] - round(12 * scale),
            box[2] + round(24 * scale), box[3] + round(18 * scale),
        )
        headline_boxes.append(headline_box)
        headline_area += max(0, headline_box[2] - headline_box[0]) * max(
            0, headline_box[3] - headline_box[1]
        )
        draw.rounded_rectangle(
            headline_box,
            radius=round(12 * scale),
            fill=(3, 7, 12),
        )
        key_word = words[-1]
        draw.text(
            (x, y), line, font=font,
            fill=palette["accent"] if key_word in line.split() else (255, 255, 255),
            stroke_width=round(5 * scale), stroke_fill=(0, 0, 0),
        )
        y += headline_size + round(22 * scale)
    qualification = "Natural Earth boundaries; disputed status may differ"
    small_font = _font(font_path, round(19 * scale))
    draw.rounded_rectangle(
        tuple(round(value * scale) for value in (48, 666, 720, 704)),
        radius=round(8 * scale), fill=(3, 7, 12, 225)
    )
    draw.text(
        (round(58 * scale), round(674 * scale)), qualification,
        font=small_font, fill=(255, 255, 255),
    )
    badge_area = (
        width - round(200 * scale), height - round(112 * scale), width, height
    )
    target_box = (
        target_point[0] - marker_radius, target_point[1] - marker_radius,
        target_point[0] + marker_radius, target_point[1] + marker_radius,
    )
    badge_area_clear = not any(
        box[0] < badge_area[2] and box[2] > badge_area[0]
        and box[1] < badge_area[3] and box[3] > badge_area[1]
        for box in [*headline_boxes, target_box]
    )
    headline_block_coverage = headline_area / (width * height)
    master = image.resize(
        (MASTER_WIDTH, MASTER_HEIGHT), Image.Resampling.LANCZOS
    )
    saturation = ImageStat.Stat(master.convert("HSV")).mean[1] / 255
    output_path.parent.mkdir(parents=True, exist_ok=True)
    master.save(output_path, format="PNG", optimize=True)
    score = _score_concept(
        headline, topic, round(headline_size / SUPERSAMPLE_FACTOR), True,
        RENDER_SCALE,
        headline_block_coverage, saturation,
        arrow_count=1, layout_variety=layout_variety,
        badge_area_clear=badge_area_clear,
    )
    return score, headline_size


def generate_thumbnail_concepts(
    topic: str,
    country_iso_a3: str,
    output_dir: Path,
    data_root: Path,
    *,
    headline: str | None = None,
) -> dict[str, Any]:
    """Create three original concepts, score them, and save source recipes/previews."""
    if not topic.strip():
        raise ThumbnailEngineError("A documentary topic is required.")
    short_headline = _headline_for(topic, headline)
    collection, dataset = load_natural_earth(data_root, scale=50)
    target = find_country(collection, country_iso_a3)
    country_name = str(
        target.get("properties", {}).get("ADMIN")
        or target.get("properties", {}).get("NAME")
        or country_iso_a3
    )
    font_path = _find_bold_font()
    concepts_dir = output_dir / "thumbnail_concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    layout_signatures = {
        (
            concept["map_anchor"],
            tuple(concept["headline_anchor"]),
            concept["arrow_style"],
            tuple(sorted(concept["palette"].items())),
        )
        for concept in CONCEPTS
    }
    layouts_are_distinct = len(layout_signatures) == len(CONCEPTS)
    entries: list[dict[str, Any]] = []
    for concept in CONCEPTS:
        image_path = concepts_dir / f"{concept['id']}.png"
        score, font_size = _render_concept(
            topic, short_headline, target, collection, concept, image_path,
            font_path, layouts_are_distinct,
        )
        recipe = {
            "renderer": "GeoFactory thumbnail_engine",
            "renderer_version": 1,
            "topic": topic,
            "country_iso_a3": country_iso_a3.upper(),
            "country_name": country_name,
            "headline": short_headline,
            "master_dimensions": [MASTER_WIDTH, MASTER_HEIGHT],
            "platform_dimensions": [THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT],
            "render_dimensions_before_downsample": [
                MASTER_WIDTH * SUPERSAMPLE_FACTOR,
                MASTER_HEIGHT * SUPERSAMPLE_FACTOR,
            ],
            "dataset_name": dataset["dataset_name"],
            "dataset_version": dataset["dataset_version"],
            "dataset_licence": dataset["licence"],
            "dataset_download_date": dataset["download_date"],
            "dataset_sha256": dataset["sha256"],
            "supersample_factor": SUPERSAMPLE_FACTOR,
            "concept": concept,
            "font_size_px": round(font_size / SUPERSAMPLE_FACTOR),
            "qualification": "Natural Earth boundaries; disputed status may differ",
            "no_logo_or_channel_branding": True,
        }
        source_path = concepts_dir / f"{concept['id']}.source.json"
        source_path.write_text(
            json.dumps(recipe, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        entries.append({
            "concept_id": concept["id"],
            "image": str(image_path.relative_to(output_dir)),
            "editable_source": str(source_path.relative_to(output_dir)),
            **score,
        })
    winner = max(entries, key=lambda entry: (entry["scores"]["overall"], entry["concept_id"]))
    winner_path = output_dir / "thumbnail.jpg"
    master_path = output_dir / "thumbnail_master.jpg"
    winner_image = output_dir / winner["image"]
    with Image.open(winner_image) as opened:
        master = opened.convert("RGB")
        master.save(master_path, "JPEG", quality=95, optimize=True)
        platform_image = master.resize(
            (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS
        )
        platform_image.save(winner_path, "JPEG", quality=94, optimize=True)
        mobile = platform_image.resize((160, 90), Image.Resampling.LANCZOS)
        mobile.save(output_dir / "thumbnail_mobile_preview.jpg", "JPEG", quality=90)
    contact = Image.new("RGB", (1200, 225), (16, 20, 25))
    for index, entry in enumerate(entries):
        with Image.open(output_dir / entry["image"]) as opened:
            contact.paste(opened.convert("RGB").resize((400, 225), Image.Resampling.LANCZOS),
                          (index * 400, 0))
    contact.save(output_dir / "thumbnail_contact_sheet.jpg", "JPEG", quality=90)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "country_iso_a3": country_iso_a3.upper(),
        "country_name": country_name,
        "headline": short_headline,
        "dataset": {
            "name": dataset["dataset_name"],
            "version": dataset["dataset_version"],
            "licence": dataset["licence"],
            "download_date": dataset["download_date"],
            "sha256": dataset["sha256"],
        },
        "scoring_notice": (
            "Heuristic design checks only; scores do not predict views, factual completeness, "
            "or success. Human review of map context and title accuracy is required."
        ),
        "winner": winner["concept_id"],
        "winner_scores": winner["scores"],
        "concepts": entries,
        "outputs": {
            "winner": str(winner_path),
            "master": str(master_path),
            "contact_sheet": str(output_dir / "thumbnail_contact_sheet.jpg"),
            "mobile_preview": str(output_dir / "thumbnail_mobile_preview.jpg"),
        },
    }
    (output_dir / "thumbnail_scores.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result
