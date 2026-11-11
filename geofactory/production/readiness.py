"""Measurable production-readiness gates, deliberately independent of rendering."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from geofactory.production.models import ClaimEvidence, PreproductionPlan
from geofactory.production.research import audit_research

STATUSES = {"MET", "PARTIAL", "MISSING", "NOT_TESTED"}


@dataclass(frozen=True)
class QualityCheck:
    category: str
    status: str
    metric: str
    observed: str
    threshold: str
    action: str

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES or self.status not in STATUSES:
            raise ValueError("Unknown readiness category or status")


CATEGORIES = (
    "storytelling_and_narration", "visual_relevance_and_quality", "maps_and_geographic_accuracy",
    "animation_and_motion_design", "cinematic_footage", "infographics_and_typography",
    "editing_and_transitions", "audio_and_sound_design", "color_consistency",
    "pacing_and_retention", "factual_accuracy", "asset_provenance_and_licensing",
)


def evaluate_preproduction(
    plan: PreproductionPlan,
    claims: list[ClaimEvidence],
    *,
    runtime_verified_engines: Iterable[str],
    approved_asset_ids: Iterable[str] = (),
    human_story_approved: bool = False,
    human_geography_approved: bool = False,
) -> list[QualityCheck]:
    """Assess planning evidence only; final audiovisual checks remain NOT_TESTED."""
    plan.validate()
    engines = set(runtime_verified_engines)
    approved = set(approved_asset_ids)
    research = audit_research(plan, claims)
    blockers = [finding for finding in research if finding.severity == "blocker"]
    scenes = plan.scenes
    downgrades = [scene.scene_id for scene in scenes if scene.fallback_from]
    unassigned_geo = [scene.scene_id for scene in scenes if any(g.native_crs == "UNASSIGNED" for g in scene.geographic_requirements)]
    missing_runtime = sorted({scene.motion_engine for scene in scenes} - engines)
    max_scene = max(scene.end_s - scene.start_s for scene in scenes)
    claim_ids = {claim.claim_id for claim in claims}
    linked_assets = sum(bool(set().union(*(set(b.required_source_ids) for b in scene.asset_briefs)) & claim_ids) for scene in scenes)

    checks = [
        QualityCheck("storytelling_and_narration", "MET" if human_story_approved else "PARTIAL", "central question + human story approval", f"question present; approval={human_story_approved}", "both required", "Conduct table read and approve hook, causality, payoff and narration"),
        QualityCheck("visual_relevance_and_quality", "PARTIAL" if linked_assets == len(scenes) else "MISSING", "scenes with claim-linked asset briefs", f"{linked_assets}/{len(scenes)}", f"{len(scenes)}/{len(scenes)} plus final visual review", "Review actual selected assets; briefs are not finished visuals"),
        QualityCheck("maps_and_geographic_accuracy", "PARTIAL" if human_geography_approved and not unassigned_geo else "MISSING" if unassigned_geo else "PARTIAL", "CRS/dataset assignment + geographic approval", f"unassigned scenes={unassigned_geo}; approval={human_geography_approved}", "all spatial layers assigned and reviewed", "Assign versioned datasets, native/display CRS and boundary policy"),
        QualityCheck("animation_and_motion_design", "PARTIAL" if not downgrades else "MISSING", "unapproved engine downgrades", str(downgrades), "none", "Provide required engine or redesign the shot explicitly"),
        QualityCheck("cinematic_footage", "NOT_TESTED", "shot-level relevance, stability and resolution review", "planning only", "100% selected shots reviewed", "Source and inspect footage; no automatic quality claim"),
        QualityCheck("infographics_and_typography", "NOT_TESTED", "safe-area, unit, source and legibility review", "planning only", "0 critical layout/data errors", "Review representative stills and motion when rendering is separately approved"),
        QualityCheck("editing_and_transitions", "NOT_TESTED", "continuity and motivated transition review", "planning only", "0 unmotivated or broken transitions", "Perform timeline review after production approval"),
        QualityCheck("audio_and_sound_design", "NOT_TESTED", "speech quality, sync, ducking, loudness and true peak", "direction present; no listening test", "-16 LUFS-I, <=-1.5 dBTP and human listening approval", "Audition licensed voice, music, ambience and mix"),
        QualityCheck("color_consistency", "NOT_TESTED", "shot matching and display-referred output review", "planning only", "0 visible mismatch in human review", "Define show LUT/grade and test across representative footage"),
        QualityCheck("pacing_and_retention", "PARTIAL" if max_scene <= 18 else "MISSING", "maximum planned scene duration", f"{max_scene:.2f}s", "<=18s planning heuristic; retention requires table read", "Split monotonous beats and review information density"),
        QualityCheck("factual_accuracy", "MET" if not blockers and claims else "MISSING", "blocking research findings", str(len(blockers)), "0 and >=1 verified claim", "Resolve every source/review/coverage blocker"),
        QualityCheck("asset_provenance_and_licensing", "PARTIAL" if not approved else "MISSING", "approved asset ids", str(len(approved)), "every used asset rights-reviewed with attribution", "Register source, creator, licence, transformations and hashes"),
    ]
    if missing_runtime:
        checks.append(QualityCheck("animation_and_motion_design", "MISSING", "runtime-verified motion engines", f"missing={missing_runtime}", "all selected engines runtime-verified", "Repair runtime or revise treatment before production"))
    return checks


def readiness_decision(checks: Iterable[QualityCheck]) -> str:
    statuses = {check.status for check in checks}
    return "READY_FOR_HUMAN_PREPRODUCTION_REVIEW" if "MISSING" not in statuses else "NOT_READY"
