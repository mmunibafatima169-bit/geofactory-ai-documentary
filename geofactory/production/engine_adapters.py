"""Reusable engine configuration and fail-closed non-rendering preflight."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from geofactory.production.capabilities import Capability, executable_probe, python_import_probe


@dataclass(frozen=True)
class EngineEnvironment:
    engine: str
    interpreter: str
    module: str
    version_expression: str
    purpose: str

    def probe(self) -> Capability:
        return python_import_probe(self.engine, self.interpreter, self.module, self.version_expression)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_environments() -> dict[str, EngineEnvironment]:
    root = repository_root()
    return {
        "blender": EngineEnvironment("blender", str(root / ".venv-blender/bin/python"), "bpy", "bpy.app.version_string", "terrain, environments, engineering objects and camera animation"),
        "manim": EngineEnvironment("manim", str(root / ".venv-manim/bin/python"), "manim", "manim.__version__", "technical and scientific explanations"),
    }


@dataclass(frozen=True)
class PreparationJob:
    scene_id: str
    engine: str
    operation: str
    input_contract: str
    output_contract: str
    executable: bool
    blocker: str | None


def build_preparation_job(scene_id: str, engine: str, capability: Capability) -> PreparationJob:
    contracts = {
        "blender": ("blender_scene_config", "TerrainConfig/EnvironmentConfig/CameraConfig JSON", "editable .blend scene; no automatic render"),
        "manim": ("manim_scene_config", "validated data/notation/explanation JSON", "Manim scene configuration; no automatic render"),
        "gis": ("geospatial_preparation", "versioned vector/raster + CRS + provenance", "derived GeoJSON/GeoTIFF + lineage report"),
    }
    operation, inputs, outputs = contracts.get(engine, ("remotion_composition", "typed scene intent", "composition properties"))
    blocker = None if capability.runtime_verified else capability.detail
    return PreparationJob(scene_id, engine, operation, inputs, outputs, capability.runtime_verified, blocker)


def collect_capabilities(*, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe", remotion_workdir: Path | None = None) -> dict[str, Capability]:
    """Probe all orchestrator dependencies without invoking any renderer."""
    root = repository_root()
    capabilities = {name: environment.probe() for name, environment in default_environments().items()}
    main_python = str(root / ".venv/bin/python")
    capabilities["gis"] = python_import_probe("gis", main_python, "geopandas", "geopandas.__version__")
    capabilities["ffmpeg"] = executable_probe("ffmpeg", ffmpeg, ("-version",))
    capabilities["ffprobe"] = executable_probe("ffprobe", ffprobe, ("-version",))
    workdir = remotion_workdir or root / "studio/remotion"
    try:
        import subprocess
        result = subprocess.run(["npx", "remotion", "versions"], cwd=workdir, capture_output=True, text=True, timeout=60, check=False)
        first = next((line.strip() for line in result.stdout.splitlines() if line.startswith("On version:")), None)
        aligned = "All packages have the correct version" in result.stdout
        capabilities["remotion"] = Capability("remotion", result.returncode == 0, result.returncode == 0 and aligned, first, "npx", "version/alignment probe only; no render")
    except (OSError, subprocess.SubprocessError) as exc:
        capabilities["remotion"] = Capability("remotion", False, False, None, "npx", str(exc))
    return capabilities


def write_engine_report(destination: Path) -> dict:
    environments = default_environments()
    capabilities = {name: environment.probe() for name, environment in environments.items()}
    payload = {"video_rendered": False, "engines": {name: capability.to_dict() for name, capability in capabilities.items()}}
    Path(destination).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
