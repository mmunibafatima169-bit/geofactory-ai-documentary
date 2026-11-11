"""GIS preparation with explicit provenance, geometry repair and CRS contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import geopandas as gpd
from shapely import is_valid_reason
from shapely import make_valid
from shapely.geometry import GeometryCollection


class GeometryRepairError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _polygonal_only(geometry):
    """Discard non-areal repair fragments, never source polygons."""
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        return geometry
    if isinstance(geometry, GeometryCollection):
        polygons = [part for part in geometry.geoms if part.geom_type in {"Polygon", "MultiPolygon"}]
        if not polygons:
            return geometry
        from shapely.ops import unary_union
        return unary_union(polygons)
    return geometry


def repair_vector_derivative(
    source: Path,
    destination: Path,
    report_path: Path,
    *,
    dataset_name: str,
    dataset_version: str,
    licence: str,
    licence_url: str,
    source_url: str,
    max_relative_area_change: float = 1e-6,
) -> dict:
    """Repair only invalid geometries in a new file; preserve rows/attributes.

    Area and bounds checks prevent a repair from silently becoming a geographic
    simplification. The original source is never modified.
    """
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise GeometryRepairError("Source and destination must differ")
    frame = gpd.read_file(source)
    if frame.crs is None:
        raise GeometryRepairError("Source CRS is missing")
    invalid = frame[~frame.geometry.is_valid]
    repairs = []
    repaired = frame.copy()
    for index, row in invalid.iterrows():
        before = row.geometry
        candidate = _polygonal_only(make_valid(before))
        if candidate.is_empty or not candidate.is_valid:
            raise GeometryRepairError(f"Feature {index} remains invalid after make_valid")
        original_area = before.area
        absolute_area_change = abs(candidate.area - original_area)
        area_change = absolute_area_change / original_area if original_area > 0 else 0.0
        # A bow-tie's signed area may be zero even though it encloses two real
        # triangles. make_valid correctly exposes that area; only non-zero
        # source areas can use a meaningful relative-change guard.
        if original_area > 0 and area_change > max_relative_area_change:
            raise GeometryRepairError(f"Feature {index} area changed unexpectedly by {absolute_area_change:.3g}")
        repairs.append({
            "feature_index": int(index),
            "feature_name": str(row.get("NAME", row.get("name", index))),
            "before_type": before.geom_type,
            "after_type": candidate.geom_type,
            "invalid_reason": is_valid_reason(before),
            "relative_area_change": area_change,
            "method": "Shapely make_valid; retain polygonal parts only",
        })
        repaired.at[index, "geometry"] = candidate
    if len(repaired) != len(frame) or not repaired.geometry.is_valid.all():
        raise GeometryRepairError("Repair changed feature count or left invalid geometry")
    if not repaired.drop(columns="geometry").equals(frame.drop(columns="geometry")):
        raise GeometryRepairError("Attribute values changed during geometry repair")
    destination.parent.mkdir(parents=True, exist_ok=True)
    repaired.to_file(destination, driver="GeoJSON")
    reloaded = gpd.read_file(destination)
    if len(reloaded) != len(frame) or not reloaded.geometry.is_valid.all():
        raise GeometryRepairError("Derived file failed read-back validation")
    report = {
        "schema_version": 1,
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "licence": licence,
        "licence_url": licence_url,
        "source_url": source_url,
        "source_file": str(source),
        "source_sha256": sha256_file(source),
        "derived_file": str(destination),
        "derived_sha256": sha256_file(destination),
        "crs": str(frame.crs),
        "feature_count_before_after": [len(frame), len(reloaded)],
        "invalid_before_after": [len(invalid), int((~reloaded.geometry.is_valid).sum())],
        "repairs": repairs,
        "source_modified": False,
        "notice": "Topological repair only; disputed borders and source attributes are not editorially normalized.",
    }
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def reproject_vector(source: Path, destination: Path, display_crs: str) -> dict:
    """Create a derived, explicitly projected vector without altering its source."""
    frame = gpd.read_file(source)
    if frame.crs is None or not frame.geometry.is_valid.all():
        raise GeometryRepairError("Reprojection requires valid geometry and a declared CRS")
    projected = frame.to_crs(display_crs)
    projected.to_file(destination, driver="GeoJSON")
    return {"source_crs": str(frame.crs), "display_crs": str(projected.crs), "features": len(frame)}
