"""Cross-domain production gates for tools, assets, sound and incomplete data."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from geofactory.production.audio import AudioMixPlan, AudioError
from geofactory.production.capabilities import Capability
from geofactory.production.models import PreproductionPlan
from geofactory.production.quality_standards import assess_plan_standards


@dataclass(frozen=True)
class GateFinding:
    severity: str  # blocker | warning
    domain: str
    code: str
    message: str


def evaluate_production_gates(
    plan: PreproductionPlan,
    capabilities: dict[str, Capability],
    *,
    resolved_assets: dict[str, tuple[str, ...]],
    approved_assets: set[str],
    audio_mix: AudioMixPlan | None = None,
    voice_quality_approved: bool = False,
    satellite_live_verified: bool = False,
    terrain_runtime_verified: bool = False,
) -> list[GateFinding]:
    plan.validate()
    findings = [GateFinding("blocker", "editorial", finding.code, finding.message) for finding in assess_plan_standards(plan)]
    required_engines = {scene.preparation_engine for scene in plan.scenes} | {scene.motion_engine for scene in plan.scenes} | {"remotion", "ffmpeg"}
    for engine in sorted(required_engines):
        capability = capabilities.get(engine)
        if capability is None or not capability.runtime_verified:
            findings.append(GateFinding("blocker", "tools", "engine_unavailable", f"{engine}: {capability.detail if capability else 'not probed'}"))
    for scene in plan.scenes:
        resolved = set(resolved_assets.get(scene.scene_id, ()))
        if len(resolved) < len(scene.asset_briefs):
            findings.append(GateFinding("blocker", "assets", "asset_brief_unresolved", f"{scene.scene_id} has {len(resolved)}/{len(scene.asset_briefs)} required asset selections"))
        unapproved = resolved - approved_assets
        if unapproved:
            findings.append(GateFinding("blocker", "licensing", "asset_rights_unapproved", f"{scene.scene_id}: {sorted(unapproved)}"))
        if scene.fallback_from:
            findings.append(GateFinding("blocker", "tools", "unapproved_engine_downgrade", f"{scene.scene_id}: {scene.fallback_from}→{scene.motion_engine}"))
        for geo in scene.geographic_requirements:
            if geo.dataset_source.startswith("UNASSIGNED") or geo.native_crs == "UNASSIGNED" or geo.display_crs.startswith("UNASSIGNED"):
                findings.append(GateFinding("blocker", "geography", "geo_contract_incomplete", f"{scene.scene_id}: dataset and CRS are unassigned"))
        if scene.visual_technique == "satellite_context" and not satellite_live_verified:
            findings.append(GateFinding("blocker", "satellite", "live_imagery_unverified", f"{scene.scene_id}: provider acquisition and attribution not verified"))
        if scene.visual_technique == "terrain_3d" and not terrain_runtime_verified:
            findings.append(GateFinding("blocker", "terrain", "terrain_runtime_unverified", f"{scene.scene_id}: Blender/DEM pipeline not verified"))
    if not voice_quality_approved:
        findings.append(GateFinding("blocker", "audio", "voice_quality_unapproved", "Pronunciation, consistency and naturalness require human approval"))
    if audio_mix is None:
        findings.append(GateFinding("blocker", "audio", "audio_mix_missing", "No scene-linked audio mix plan was supplied"))
    else:
        try:
            audio_mix.validate(plan)
        except AudioError as exc:
            findings.append(GateFinding("blocker", "audio", "audio_mix_invalid", str(exc)))
    return findings


def readiness_summary(findings: list[GateFinding]) -> dict:
    blockers = [finding for finding in findings if finding.severity == "blocker"]
    return {"ready": not blockers, "blocker_count": len(blockers), "warning_count": len(findings) - len(blockers), "findings": [asdict(finding) for finding in findings], "video_render_authorized": False}
