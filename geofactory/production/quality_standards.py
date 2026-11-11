"""Common professional standards with subject-specific visual policies."""

from __future__ import annotations

from dataclasses import dataclass

from geofactory.production.models import PreproductionPlan


@dataclass(frozen=True)
class StandardFinding:
    code: str
    message: str
    scene_id: str | None = None


COMMON_MINIMUMS = {
    "max_scene_seconds": 30.0,
    "minimum_resolution": (1920, 1080),
    "audio_sample_rate": 48000,
    "target_lufs": -16.0,
    "true_peak_dbtp": -1.5,
}

SUBJECT_VISUAL_POLICIES = {
    "geography": {"gis_map", "satellite_context", "route_animation", "live_action", "data_chart"},
    "infrastructure": {"engineering_cutaway", "mechanism_3d", "terrain_3d", "live_action", "data_chart"},
    "disaster": {"hazard_sequence", "timeline_reconstruction", "satellite_context", "archival_footage", "live_action"},
    "economics": {"data_chart", "economic_flow", "comparison_layout", "map_context", "live_action"},
    "general": {"live_action", "archival_footage", "data_chart", "typographic_explanation"},
}


def assess_plan_standards(plan: PreproductionPlan) -> list[StandardFinding]:
    plan.validate()
    findings = []
    for scene in plan.scenes:
        if scene.end_s - scene.start_s > COMMON_MINIMUMS["max_scene_seconds"]:
            findings.append(StandardFinding("scene_too_long", "Scene exceeds the common pacing ceiling", scene.scene_id))
        if not scene.claim_ids:
            findings.append(StandardFinding("claim_link_missing", "Every scene must link to the claim ledger", scene.scene_id))
        if not scene.asset_briefs:
            findings.append(StandardFinding("asset_brief_missing", "Every scene needs an actionable asset brief", scene.scene_id))
        if scene.audio is None:
            findings.append(StandardFinding("audio_direction_missing", "Every scene needs sound direction", scene.scene_id))
        if scene.visual_technique not in SUBJECT_VISUAL_POLICIES[plan.profile.subject]:
            findings.append(StandardFinding("subject_treatment_review", f"{scene.visual_technique} requires explicit editorial justification for {plan.profile.subject}", scene.scene_id))
    techniques = {scene.visual_technique for scene in plan.scenes}
    if len(plan.scenes) >= 4 and len(techniques) < 2:
        findings.append(StandardFinding("visual_monotony", "Longer plans must not use one visual template for every scene"))
    return findings
