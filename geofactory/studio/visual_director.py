"""AI Visual Director v1: choose the rendering engine per narration segment.

Deterministic rules over the segmented narration. Each decision records a
rationale so a human (or a future LLM-backed director) can audit or override
it. Engine availability is respected: an unavailable engine falls back to the
next best one and the degradation is recorded in the rationale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from geofactory.studio.scene_manifest import SceneManifest, ScenePlan

# Keyword families → (visual_objective, preferred engine, animation, camera)
_RULES: list[tuple[re.Pattern[str], str, str, str, str, str]] = [
    (re.compile(r"\b(mose|barrier|engineering|construct|inlet|gate|foundation|underground|cross.section)\b", re.I),
     "engineering_demo", "blender", "exploded_view", "dolly_orbit",
     "engineering mechanism or subsurface structure needs a spatial explanation"),
    (re.compile(r"\b(percent|centimetre|metre|million|billion|century|\b19\d\d|\b20\d\d|data|level|rate|project)\b", re.I),
     "data_chart", "manim", "animated_graph", "static",
     "numeric/temporal claim needs a sourced graph or comparison, not decoration"),
    (re.compile(r"\b(map|border|country|continent|island|lagoon|coast|territor|inlet|where|location)\b", re.I),
     "map_context", "remotion", "map_highlight", "push_in",
     "geographic relationship is the claim, so an animated map is primary evidence"),
    (re.compile(r"\b(flood|1966|storm|historic|archive|before|past|photograph)\b", re.I),
     "archival_footage", "ffmpeg", "licensed_archival_clip", "push_in",
     "historical beat benefits from authentic archival moving images or photographs"),
    (re.compile(r"\b(city|street|canal|people|gondola|today|daily|building|water)\b", re.I),
     "cinematic_footage", "ffmpeg", "licensed_relevant_clip", "push_in",
     "observable place/activity is better established by relevant real footage"),
    (re.compile(r"\b(jakarta|bangkok|new orleans|shanghai|other cities|around the world|bigger picture|many cities)\b", re.I),
     "comparison_montage", "remotion", "split_screen_compare", "pull_back",
     "comparison beat needs multiple labelled geographies in one visual system"),
    (re.compile(r"\b(satellite|aerial|from above|terrain|elevation|coastline)\b", re.I),
     "satellite_imagery", "remotion", "layered_aerial_map", "push_in",
     "top-down spatial evidence clarifies terrain/coastline relationships"),
]

FALLBACK_ENGINE = {"blender": "manim", "manim": "remotion", "remotion": "ffmpeg", "ffmpeg": "ffmpeg"}

MAX_SCENE_SECONDS = 22.0


@dataclass(frozen=True)
class Segment:
    """One narration segment with timing (typically one SRT cue or a sentence group)."""
    text: str
    start_s: float
    end_s: float


def _sentence_ranges(text: str, start_s: float, end_s: float) -> list[Segment]:
    """Split a narration block into sentence-timed segments, sharing time
    proportionally to sentence length."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return [Segment(text.strip(), start_s, end_s)]
    weights = [max(1, len(s)) for s in sentences]
    total = float(sum(weights))
    span = end_s - start_s
    cursor = start_s
    out: list[Segment] = []
    for sentence, weight in zip(sentences, weights, strict=True):
        seg_end = end_s if sentence is sentences[-1] else cursor + span * weight / total
        out.append(Segment(sentence, cursor, seg_end))
        cursor = seg_end
    return out


def plan_scenes(
    job_id: str,
    title: str,
    segments: list[Segment],
    *,
    engines_available: set[str] | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> SceneManifest:
    """Build a validated scene manifest from timed narration segments."""
    available = engines_available or {"remotion", "ffmpeg"}
    scenes: list[ScenePlan] = []
    queue: list[Segment] = []
    cursor = 0.0

    def flush(end_s: float) -> None:
        nonlocal queue, cursor
        if not queue:
            return
        text = " ".join(s.text for s in queue)
        scenes.append(_direct(job_id, len(scenes) + 1, text, queue[0].start_s, end_s, available))
        queue = []
        cursor = end_s

    for seg in segments:
        if cursor and seg.start_s > cursor + 1.2:
            flush(cursor)
        queue.append(seg)
        cursor = seg.end_s
        if cursor - queue[0].start_s >= MAX_SCENE_SECONDS:
            flush(cursor)
    flush(cursor)

    manifest = SceneManifest(
        job_id=job_id, title=title, fps=fps, width=width, height=height, scenes=scenes
    )
    manifest.validate()
    return manifest


def rank_visual_treatments(
    text: str,
    recent: list[tuple[str, str]] | None = None,
) -> list[tuple[int, tuple[re.Pattern[str], str, str, str, str, str], str]]:
    """Rank all appropriate visual treatments with an explicit variety penalty.

    Multiple semantic matches matter: a numeric engineering sentence may prefer
    an explanatory chart over a generic engineering shot. Recent objective and
    engine reuse is penalised to prevent template repetition.
    """
    recent = recent or []
    ranked: list[tuple[int, tuple[re.Pattern[str], str, str, str, str, str], str]] = []
    lower = text.lower()
    for rule in _RULES:
        pattern, objective, engine, _animation, _camera, _why = rule
        matches = pattern.findall(text)
        if not matches:
            continue
        score = 42 + min(36, 12 * len(matches))
        if objective == "data_chart" and re.search(r"\d|percent|centimetre|metre|million|billion", lower):
            score += 18
        if objective == "map_context" and re.search(r"where|between|across|inside|coast|inlet", lower):
            score += 16
        if objective == "archival_footage" and re.search(r"\b(18|19|20)\d\d\b|historic|before", lower):
            score += 18
        if objective == "engineering_demo" and re.search(r"how|beneath|through|swing|compressed|layer", lower):
            score += 16
        objective_repeat = sum(o == objective for o, _ in recent)
        engine_repeat = sum(e == engine for _, e in recent)
        penalty = objective_repeat * 24 + engine_repeat * 7
        score -= penalty
        reason = (
            f"semantic={42 + min(36, 12 * len(matches))}; "
            f"variety_penalty={penalty}; matches={len(matches)}"
        )
        ranked.append((score, rule, reason))
    return sorted(ranked, key=lambda item: item[0], reverse=True)


def _direct(
    job_id: str, n: int, text: str, start_s: float, end_s: float,
    available: set[str], recent: list[tuple[str, str]] | None = None,
) -> ScenePlan:
    objective, engine, animation, camera, rationale = (
        "photo_evidence", "ffmpeg", "ken_burns_photo", "push_in",
        "general beat: source a claim-relevant licensed visual",
    )
    ranked = rank_visual_treatments(text, recent)
    if ranked:
        score, (_pattern, objective, engine, animation, camera, rationale), breakdown = ranked[0]
        alternatives = ", ".join(f"{item[1][1]}={item[0]}" for item in ranked[1:3]) or "none"
        rationale += f"; director score={score} ({breakdown}); alternatives: {alternatives}"
    if engine not in available:
        original = engine
        while engine not in available and engine != "ffmpeg":
            engine = FALLBACK_ENGINE[engine]
        rationale += f"; {original} unavailable here → fallen back to {engine}"
    overlays = _overlays_for(objective, text)
    transition = "cut"
    if n == 1:
        transition = "zoom_punch"
    elif objective == "comparison_montage":
        transition = "wipe_map"
    elif objective == "engineering_demo":
        transition = "dip_to_black"
    return ScenePlan(
        scene_id=f"sc-{n:03d}",
        narration=text,
        start_s=round(start_s, 3),
        end_s=round(end_s, 3),
        visual_objective=objective,
        engine=engine,
        animation_type=animation,
        camera=camera,
        text_overlays=overlays,
        transition=transition,
        sound_fx=["sting_title"] if n == 1 else [],
        source_ids=_claim_ids(text),
        rationale=rationale,
    )


def _overlays_for(objective: str, text: str) -> list[str]:
    if objective == "map_context":
        return ["location_label"]
    if objective == "engineering_demo":
        return ["part_callouts"]
    if objective == "data_chart":
        return ["axis_labels", "headline_number"]
    if objective == "comparison_montage":
        return ["city_labels"]
    return []


def _claim_ids(text: str) -> list[str]:
    return re.findall(r"\[(clm-[a-z0-9-]+)\]", text)


def segments_from_narration(narration_text: str, total_seconds: float) -> list[Segment]:
    """Timing helper when no SRT exists yet: spread sentences across the
    planned duration proportionally to sentence length."""
    return _sentence_ranges(narration_text, 0.0, float(total_seconds))
