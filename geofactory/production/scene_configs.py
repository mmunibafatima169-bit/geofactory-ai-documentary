"""Engine-neutral terrain/environment/camera and scientific scene schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TerrainConfig:
    dem_path: str
    texture_path: str | None
    vertical_exaggeration: float
    subdivisions: int
    vertical_datum: str
    source_attribution: str


@dataclass(frozen=True)
class EnvironmentConfig:
    world_colour: tuple[float, float, float]
    sun_energy: float
    sun_rotation_deg: tuple[float, float, float]
    material_roughness: float = 0.8


@dataclass(frozen=True)
class CameraKey:
    frame: int
    location: tuple[float, float, float]
    target: tuple[float, float, float]
    lens_mm: float = 35.0


@dataclass(frozen=True)
class BlenderSceneConfig:
    terrain: TerrainConfig
    environment: EnvironmentConfig
    camera_keys: tuple[CameraKey, ...]
    fps: int = 30
    resolution: tuple[int, int] = (1920, 1080)

    def validate(self) -> None:
        if not self.terrain.dem_path or self.terrain.vertical_exaggeration <= 0:
            raise ValueError("DEM and positive vertical exaggeration are required")
        if self.terrain.vertical_datum.startswith("UNDECLARED") or not self.terrain.source_attribution.strip():
            raise ValueError("Vertical datum and attribution must be reviewed")
        if not 16 <= self.terrain.subdivisions <= 1024:
            raise ValueError("Subdivisions must be bounded for host memory")
        if len(self.camera_keys) < 2 or [key.frame for key in self.camera_keys] != sorted(key.frame for key in self.camera_keys):
            raise ValueError("At least two chronological camera keys are required")
        if self.fps <= 0 or min(self.resolution) <= 0:
            raise ValueError("Invalid output settings")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ScientificExplanationConfig:
    explanation_kind: str
    title: str
    labels: tuple[str, ...]
    values: tuple[float, ...]
    unit: str
    source_ids: tuple[str, ...]
    note: str

    def validate(self) -> None:
        if self.explanation_kind not in {"line_graph", "bar_comparison", "formula_sequence", "labelled_process"}:
            raise ValueError("Unsupported scientific explanation")
        if not self.title.strip() or not self.unit.strip() or not self.source_ids:
            raise ValueError("Scientific explanation needs title, unit and sources")
        if self.explanation_kind in {"line_graph", "bar_comparison"} and (len(self.labels) != len(self.values) or not self.values):
            raise ValueError("Chart labels and values must be non-empty and aligned")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)
