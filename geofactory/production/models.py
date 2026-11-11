"""Typed pre-production contracts. These models never invoke a renderer."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

SUBJECTS = {"geography", "infrastructure", "disaster", "economics", "general"}
ENGINES = {"remotion", "blender", "manim", "ffmpeg", "gis"}
VISUAL_TECHNIQUES = {
    "live_action", "archival_footage", "satellite_context", "gis_map",
    "terrain_3d", "route_animation", "engineering_cutaway", "mechanism_3d",
    "timeline_reconstruction", "hazard_sequence", "data_chart",
    "economic_flow", "comparison_layout", "typographic_explanation",
}


class ContractError(ValueError):
    """A production plan is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class DocumentaryProfile:
    subject: str
    working_title: str
    central_question: str
    audience: str = "informed general audience"
    target_runtime_s: int = 600
    tone: str = "evidence-led, visually clear, unsensational"

    def validate(self) -> None:
        if self.subject not in SUBJECTS:
            raise ContractError(f"Unsupported documentary subject: {self.subject}")
        if not self.working_title.strip() or not self.central_question.strip():
            raise ContractError("A title and central editorial question are required")
        if not 480 <= self.target_runtime_s <= 900:
            raise ContractError("Target runtime must be within 8–15 minutes")


@dataclass(frozen=True)
class ClaimEvidence:
    claim_id: str
    text: str
    source_ids: tuple[str, ...]
    review_status: str = "unreviewed"  # unreviewed | verified | disputed
    independent_source_count: int = 0


@dataclass(frozen=True)
class AssetBrief:
    purpose: str
    media_kind: str
    query_or_specification: str
    required_source_ids: tuple[str, ...] = ()
    minimum_width: int = 1920
    minimum_height: int = 1080
    rights_review_required: bool = True


@dataclass(frozen=True)
class GeographicRequirement:
    layer: str
    dataset_source: str
    native_crs: str
    display_crs: str
    geometry_role: str
    disputed_boundaries_policy: str = "show source status; never silently normalize disputes"


@dataclass(frozen=True)
class AudioDirection:
    narration_brief: str
    music_role: str
    ambience: str
    ducking_policy: str = "sidechain music under narration; target -16 LUFS-I and <= -1.5 dBTP"


@dataclass(frozen=True)
class SceneIntent:
    scene_id: str
    start_s: float
    end_s: float
    narration: str
    editorial_job: str
    visual_technique: str
    preparation_engine: str
    motion_engine: str
    rationale: str
    claim_ids: tuple[str, ...] = ()
    asset_briefs: tuple[AssetBrief, ...] = ()
    geographic_requirements: tuple[GeographicRequirement, ...] = ()
    audio: AudioDirection | None = None
    fallback_from: str | None = None
    human_approval_required: bool = True

    def validate(self) -> None:
        if not re.fullmatch(r"scene-[0-9]{3}", self.scene_id):
            raise ContractError(f"Invalid scene id: {self.scene_id}")
        if self.start_s < 0 or self.end_s <= self.start_s or self.end_s - self.start_s > 30:
            raise ContractError(f"{self.scene_id}: scene duration must be >0 and <=30 seconds")
        if self.visual_technique not in VISUAL_TECHNIQUES:
            raise ContractError(f"{self.scene_id}: unsupported visual technique")
        if self.preparation_engine not in ENGINES or self.motion_engine not in ENGINES:
            raise ContractError(f"{self.scene_id}: unsupported engine")
        if not self.narration.strip() or not self.editorial_job.strip() or not self.rationale.strip():
            raise ContractError(f"{self.scene_id}: narration, editorial job and rationale are required")
        if not self.asset_briefs:
            raise ContractError(f"{self.scene_id}: at least one actionable asset brief is required")


@dataclass(frozen=True)
class PreproductionPlan:
    schema_version: int
    profile: DocumentaryProfile
    scenes: tuple[SceneIntent, ...]
    editorial_principles: tuple[str, ...] = field(default_factory=lambda: (
        "Every factual visual must trace to the same claim ledger as the narration.",
        "Maps are evidence: retain CRS, dataset version, disputed-boundary policy and provenance.",
        "Engine substitution is a visible quality downgrade, never a silent success.",
        "No production render is permitted until automated and human readiness gates pass.",
    ))

    def validate(self) -> None:
        self.profile.validate()
        if self.schema_version != 1 or not self.scenes:
            raise ContractError("Schema version 1 and at least one scene are required")
        cursor = 0.0
        ids: set[str] = set()
        for scene in self.scenes:
            scene.validate()
            if scene.scene_id in ids or scene.start_s < cursor:
                raise ContractError("Scene ids must be unique and the timeline non-overlapping")
            ids.add(scene.scene_id)
            cursor = scene.end_s
        if cursor > self.profile.target_runtime_s + 0.001:
            raise ContractError("Planned scenes exceed target runtime")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
