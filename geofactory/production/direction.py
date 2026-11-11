"""Subject-aware visual direction with explicit, non-silent engine fallbacks."""

from __future__ import annotations

import re
from dataclasses import replace

from geofactory.production.models import (
    AssetBrief,
    AudioDirection,
    DocumentaryProfile,
    GeographicRequirement,
    PreproductionPlan,
    SceneIntent,
)

_SUBJECT_TERMS = {
    "geography": {"border", "borders", "territory", "territories", "country", "countries", "river", "rivers", "region", "regions", "island", "islands", "strait", "straits", "population", "geography"},
    "infrastructure": {"bridge", "bridges", "dam", "dams", "rail", "railway", "port", "ports", "tunnel", "tunnels", "engineering", "construction", "grid", "foundation", "foundations"},
    "disaster": {"flood", "floods", "earthquake", "earthquakes", "wildfire", "wildfires", "hurricane", "hurricanes", "cyclone", "cyclones", "disaster", "disasters", "evacuation", "evacuations", "landslide", "landslides"},
    "economics": {"economy", "economics", "trade", "market", "markets", "inflation", "gdp", "debt", "industry", "industries", "supply", "investment", "investments"},
}

# Priority is semantic, not a fixed visual template. Each treatment still needs evidence and assets.
_TREATMENTS = (
    (r"\b(route|corridor|supply chain|shipping lane|border|territor|across|between)\b", "route_animation", "gis", "remotion", "spatial relationship or flow needs a verified geographic layer"),
    (r"\b(from above|satellite|terrain|elevation|mountain|watershed|coastline)\b", "satellite_context", "gis", "remotion", "top-down spatial evidence establishes the physical setting"),
    (r"\b(terrain|valley|canyon|elevation|3d|three.dimension)\b", "terrain_3d", "gis", "blender", "relief is causal to the explanation and requires terrain geometry"),
    (r"\b(foundation|tunnel|underground|cutaway|subsurface)\b", "engineering_cutaway", "blender", "blender", "hidden structure needs a labelled spatial cutaway"),
    (r"\b(mechanism|gate|turbine|lock|piston|how it works|compressed)\b", "mechanism_3d", "blender", "blender", "mechanical operation is clearer as a controlled sequence"),
    (r"\b(gdp|inflation|debt|trade|market|percent|million|billion|trillion|rate|price|data)\b", "data_chart", "manim", "manim", "numeric evidence needs sourced axes, units and a readable comparison"),
    (r"\b(import|export|investment|industry|employment|supply|demand)\b", "economic_flow", "remotion", "remotion", "economic actors or flows need a relational visual model"),
    (r"\b(earthquake|flood|wildfire|hurricane|cyclone|landslide|evacuat)\b", "hazard_sequence", "gis", "remotion", "hazard progression needs time, exposure and geographic context"),
    (r"\b(then|before|after|timeline|century|decade|18\d\d|19\d\d|20\d\d)\b", "timeline_reconstruction", "remotion", "remotion", "change over time needs chronological visual structure"),
    (r"\b(compare|whereas|unlike|contrast|respectively)\b", "comparison_layout", "remotion", "remotion", "the narration makes a direct comparison that must remain legible"),
    (r"\b(archive|historic|photograph|footage|witness|observed)\b", "archival_footage", "ffmpeg", "ffmpeg", "authentic contemporaneous evidence is preferable to a generic reconstruction"),
)

_DEFAULT_BY_SUBJECT = {
    "geography": "gis_map",
    "infrastructure": "engineering_cutaway",
    "disaster": "hazard_sequence",
    "economics": "economic_flow",
    "general": "typographic_explanation",
}


def classify_subject(text: str) -> str:
    """Return a deterministic subject label with economics/geography tie-breaking."""
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    scores = {subject: len(tokens & terms) for subject, terms in _SUBJECT_TERMS.items()}
    best = max(scores.values(), default=0)
    return max(scores, key=scores.get) if best else "general"


def _claim_ids(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\[(clm-[a-z0-9-]+)\]", text))


def _asset_brief(technique: str, text: str, claims: tuple[str, ...]) -> AssetBrief:
    specifications = {
        "live_action": "Observational footage showing the exact place, process or human consequence in this beat",
        "archival_footage": "Dated archival moving image or still matching the event and location; verify archival caption",
        "satellite_context": "Cloud-minimized imagery with acquisition date, sensor/provider licence, bounds and attribution",
        "gis_map": "Versioned boundary/physical geography dataset with native CRS and disputed-status attributes",
        "terrain_3d": "DEM with vertical datum, resolution, acquisition source and explicit vertical exaggeration",
        "route_animation": "Verified nodes and route geometry; distinguish actual routes from schematic connections",
        "engineering_cutaway": "Dimensioned or authoritative technical reference; label illustrative reconstruction",
        "mechanism_3d": "Authoritative operating-sequence reference; no invented mechanical relationships",
        "timeline_reconstruction": "Dated primary/secondary source and matching licensed period visuals",
        "hazard_sequence": "Timestamped hazard footprint, evacuation/exposure layer and authoritative incident source",
        "data_chart": "Tidy source table with units, period, methodology, retrieval date and transformation notes",
        "economic_flow": "Sourced actor/flow values with consistent currency, year and nominal/real basis",
        "comparison_layout": "Equivalent metrics and visually matched categories for every compared item",
        "typographic_explanation": "Claim-relevant visual evidence plus restrained labels; typography is not substitute evidence",
    }
    media_kind = "data" if technique in {"data_chart", "economic_flow"} else "geodata" if technique in {"gis_map", "terrain_3d", "route_animation", "satellite_context", "hazard_sequence"} else "visual"
    return AssetBrief(specifications[technique], media_kind, text, claims)


def _geo_requirement(technique: str) -> tuple[GeographicRequirement, ...]:
    if technique not in {"gis_map", "route_animation", "satellite_context", "terrain_3d", "hazard_sequence"}:
        return ()
    layer = {"terrain_3d": "digital elevation model", "satellite_context": "dated raster imagery", "route_animation": "nodes and route lines", "hazard_sequence": "time-stamped hazard footprint"}.get(technique, "boundaries and physical geography")
    return (GeographicRequirement(layer, "UNASSIGNED — dataset and version required before production", "UNASSIGNED", "UNASSIGNED — select for map extent, not Web Mercator by default", "evidence"),)


def _audio(technique: str) -> AudioDirection:
    return AudioDirection(
        "Natural sentence-level narration; preserve names, numbers and qualifications",
        " restrained pulse for process/data; harmonic space for human consequence" if technique in {"data_chart", "economic_flow"} else "low narrative bed with a clear transition at editorial turns",
        "Location-authentic ambience when licensed; avoid decorative impacts on every label",
    )


def direct_scene(
    scene_id: str,
    narration: str,
    start_s: float,
    end_s: float,
    subject: str,
    available_engines: set[str],
    recent_techniques: tuple[str, ...] = (),
) -> SceneIntent:
    matches = []
    for priority, (pattern, technique, preparation, motion, rationale) in enumerate(_TREATMENTS):
        found = re.findall(pattern, narration, flags=re.I)
        if found:
            score = 100 - priority * 2 + min(12, len(found) * 3)
            score -= recent_techniques.count(technique) * 12
            matches.append((score, technique, preparation, motion, rationale, len(found)))
    if matches:
        _, technique, preparation, motion, rationale, match_count = max(matches, key=lambda item: item[0])
        rationale += f"; semantic matches={match_count}; repetition penalty applied"
    else:
        technique = _DEFAULT_BY_SUBJECT[subject]
        preparation = "ffmpeg" if technique == "typographic_explanation" else "gis" if technique in {"gis_map", "hazard_sequence"} else "blender" if technique == "engineering_cutaway" else "remotion"
        motion = "remotion" if technique in {"gis_map", "hazard_sequence", "economic_flow", "typographic_explanation"} else preparation
        rationale = f"subject-specific {subject} treatment; no stronger sentence-level technique matched"
    original_motion = motion
    fallback_from = None
    if motion not in available_engines:
        fallback_from = motion
        motion = "remotion" if "remotion" in available_engines else "ffmpeg"
        rationale += f"; QUALITY DOWNGRADE: {fallback_from} unavailable, manual approval required"
    claims = _claim_ids(narration)
    brief = _asset_brief(technique, narration, claims)
    return SceneIntent(
        scene_id, start_s, end_s, narration,
        "advance the central question with one claim-relevant visual idea",
        technique, preparation, motion, rationale, claims, (brief,),
        _geo_requirement(technique), _audio(technique), fallback_from,
        human_approval_required=True,
    )


def build_preproduction_plan(
    profile: DocumentaryProfile,
    timed_narration: list[tuple[float, float, str]],
    *,
    available_engines: set[str] | None = None,
) -> PreproductionPlan:
    """Create a plan only. This function has no media-generation or render path."""
    available = available_engines or {"remotion", "ffmpeg"}
    scenes: list[SceneIntent] = []
    recent: list[str] = []
    for index, (start, end, text) in enumerate(timed_narration, 1):
        scene = direct_scene(f"scene-{index:03d}", text, float(start), float(end), profile.subject, available, tuple(recent[-3:]))
        scenes.append(scene)
        recent.append(scene.visual_technique)
    plan = PreproductionPlan(1, profile, tuple(scenes))
    plan.validate()
    return plan
