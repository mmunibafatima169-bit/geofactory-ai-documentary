"""Structured per-scene production plan (scene_manifest.json).

Every scene of a documentary gets one manifest entry describing narration span,
visual objective, chosen engine, camera work, overlays, transition, sound and
source references. The renderer orchestrator and editorial QA both consume the
same manifest.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ENGINES = {"remotion", "blender", "manim", "ffmpeg"}
# Scenes may overlap by at most one cross-dissolve; anything larger means the
# plan is genuinely out of order rather than cross-faded.
MAX_TRANSITION_OVERLAP_S = 1.0
VISUAL_OBJECTIVES = {
    "cold_open", "map_zoom", "map_context", "historical_reconstruction",
    "engineering_demo", "data_chart", "timeline", "comparison_montage",
    "photo_evidence", "cinematic_footage", "archival_footage",
    "satellite_imagery", "technical_diagram", "title_card", "closing_beat",
}
CAMERA_KINDS = {"push_in", "pull_back", "pan_right", "pan_down", "dolly_orbit", "crane_rise", "static"}
TRANSITIONS = {"cut", "dip_to_black", "zoom_punch", "wipe_map"}


class ManifestError(ValueError):
    """Raised when a scene manifest entry is incomplete or inconsistent."""


@dataclass
class ScenePlan:
    scene_id: str
    narration: str
    start_s: float
    end_s: float
    visual_objective: str
    engine: str
    animation_type: str
    camera: str
    text_overlays: list[str] = field(default_factory=list)
    transition: str = "cut"
    sound_fx: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    rationale: str = ""

    def validate(self) -> None:
        if not re.fullmatch(r"sc-[0-9]{3}", self.scene_id):
            raise ManifestError(f"scene_id must look like sc-001: {self.scene_id}")
        if self.end_s <= self.start_s:
            raise ManifestError(f"{self.scene_id}: end must follow start")
        if self.end_s - self.start_s > 40:
            raise ManifestError(f"{self.scene_id}: scene longer than 40s needs splitting")
        if not self.narration.strip():
            raise ManifestError(f"{self.scene_id}: narration text required")
        if self.engine not in ENGINES:
            raise ManifestError(f"{self.scene_id}: unknown engine {self.engine}")
        if self.visual_objective not in VISUAL_OBJECTIVES:
            raise ManifestError(f"{self.scene_id}: unknown objective {self.visual_objective}")
        if self.camera not in CAMERA_KINDS:
            raise ManifestError(f"{self.scene_id}: unknown camera {self.camera}")
        if self.transition not in TRANSITIONS:
            raise ManifestError(f"{self.scene_id}: unknown transition {self.transition}")


@dataclass
class SceneManifest:
    job_id: str
    title: str
    fps: int
    width: int
    height: int
    scenes: list[ScenePlan]
    version: int = 1

    def validate(self) -> None:
        if not self.scenes:
            raise ManifestError("Manifest has no scenes")
        ids: set[str] = set()
        cursor = -1.0
        for scene in self.scenes:
            scene.validate()
            if scene.scene_id in ids:
                raise ManifestError(f"Duplicate scene id {scene.scene_id}")
            ids.add(scene.scene_id)
            if scene.start_s < cursor - MAX_TRANSITION_OVERLAP_S:
                raise ManifestError(f"{scene.scene_id}: scenes out of order or overlapping")
            cursor = scene.end_s
        if cursor <= 0 or cursor > 900:
            raise ManifestError(f"Total runtime {cursor:.1f}s outside the 8-15 minute window" if cursor > 0 else "Empty timeline")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        self.validate()
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def from_dict(data: dict) -> "SceneManifest":
        scenes = [ScenePlan(**scene) for scene in data["scenes"]]
        manifest = SceneManifest(
            job_id=str(data["job_id"]),
            title=str(data["title"]),
            fps=int(data.get("fps", 30)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            scenes=scenes,
            version=int(data.get("version", 1)),
        )
        manifest.validate()
        return manifest

    @staticmethod
    def load(path: Path) -> "SceneManifest":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"Cannot read scene manifest {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ManifestError("Scene manifest root must be a JSON object")
        return SceneManifest.from_dict(data)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
