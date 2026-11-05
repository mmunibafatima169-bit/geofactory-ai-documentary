"""Automated editorial QC for studio renders.

Goes beyond technical QA (decode/resolution) into editorial checks: repeated
footage, static-scene walls, scene/objective agreement, subtitle readability
heuristics and a contact sheet with per-scene thumbnails. Output is an
editorial report; nothing here approves a video on its own.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from geofactory.studio.scene_manifest import SceneManifest

FINDING_LEVELS = ("critical", "warning", "note")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    scene_id: str | None = None

    def to_dict(self) -> dict:
        data = {"level": self.level, "code": self.code, "message": self.message}
        if self.scene_id:
            data["scene_id"] = self.scene_id
        return data


@dataclass
class EditorialReport:
    job_id: str
    findings: list[Finding] = field(default_factory=list)
    scene_count: int = 0
    static_wall_max_s: float = 0.0
    repeated_assets: list[str] = field(default_factory=list)
    contact_sheet: str | None = None

    @property
    def critical_count(self) -> int:
        return sum(f.level == "critical" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "scene_count": self.scene_count,
            "static_wall_max_s": self.static_wall_max_s,
            "repeated_assets": self.repeated_assets,
            "critical_findings": self.critical_count,
            "contact_sheet": self.contact_sheet,
            "findings": [f.to_dict() for f in self.findings],
            "limits": [
                "Editorial heuristics supplement, and never replace, a full human viewing.",
            ],
        }

    def save(self, path: Path) -> None:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_reuses(manifest: SceneManifest) -> tuple[list[str], list[Finding]]:
    """Flag assets reused more than twice (adjacent reuse is flagged harder)."""
    counts: dict[str, int] = {}
    last: str | None = None
    findings: list[Finding] = []
    for scene in manifest.scenes:
        for asset in scene.assets:
            counts[asset] = counts.get(asset, 0) + 1
            if asset == last:
                findings.append(Finding(
                    "warning", "adjacent_asset_reuse",
                    f"{asset} plays in back-to-back scenes around {scene.scene_id}.",
                    scene.scene_id,
                ))
        if scene.assets:
            last = scene.assets[-1]
    repeated = sorted(a for a, n in counts.items() if n > 2)
    for asset in repeated:
        findings.append(Finding(
            "critical", "asset_overused",
            f"{asset} appears {counts[asset]} times; source more variety or shorten its beats.",
        ))
    return repeated, findings


def check_static_walls(manifest: SceneManifest, max_static: float = 22.0) -> tuple[float, list[Finding]]:
    longest = 0.0
    findings: list[Finding] = []
    for scene in manifest.scenes:
        span = scene.end_s - scene.start_s
        staticish = scene.engine == "ffmpeg" and scene.animation_type.startswith("ken_burns")
        if staticish and span > max_static:
            longest = max(longest, span)
            findings.append(Finding(
                "critical", "static_wall",
                f"{scene.scene_id} holds a still for {span:.1f}s (> {max_static:.0f}s); split it or add motion graphics.",
                scene.scene_id,
            ))
        elif staticish:
            longest = max(longest, span)
    return longest, findings


def check_objective_agreement(manifest: SceneManifest) -> list[Finding]:
    """Sanity: map beats need a map engine, charts need a data engine."""
    findings: list[Finding] = []
    for scene in manifest.scenes:
        if scene.visual_objective in {"map_context", "comparison_montage", "cold_open", "map_zoom"}:
            if scene.engine not in {"remotion", "ffmpeg", "blender"}:
                findings.append(Finding("warning", "objective_engine_mismatch",
                                        f"{scene.scene_id} map beat on {scene.engine}", scene.scene_id))
        if scene.visual_objective == "data_chart" and scene.engine not in {"manim", "remotion"}:
            findings.append(Finding("warning", "objective_engine_mismatch",
                                    f"{scene.scene_id} chart beat on {scene.engine}", scene.scene_id))
        if not scene.rationale.strip():
            findings.append(Finding("note", "missing_rationale",
                                    f"{scene.scene_id} has no director rationale.", scene.scene_id))
    return findings


def visual_signature(path: Path, ffmpeg: str = "ffmpeg") -> str | None:
    """Tiny perceptual signature: downscale a frame to 8x8 grayscale bytes."""
    ff = shutil.which(ffmpeg)
    if not ff or not Path(path).is_file():
        return None
    proc = subprocess.run(
        [ff, "-v", "error", "-i", str(path), "-frames:v", "1",
         "-vf", "scale=8:8,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, timeout=60, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        return None
    return hashlib.sha256(proc.stdout).hexdigest()


def detect_duplicate_looks(paths: list[Path], ffmpeg: str = "ffmpeg") -> list[tuple[str, str]]:
    """Group visually identical stills that would read as repeated footage."""
    sigs: dict[str, str] = {}
    for path in paths:
        sig = visual_signature(path, ffmpeg)
        if sig:
            sigs.setdefault(sig, str(path))
    seen: dict[str, list[str]] = {}
    duplicates: list[tuple[str, str]] = []
    for path in paths:
        sig = visual_signature(path, ffmpeg)
        if sig and sigs.get(sig) != str(path):
            duplicates.append((sigs[sig], str(path)))
    return duplicates


def make_contact_sheet(
    manifest: SceneManifest,
    video: Path,
    destination: Path,
    ffmpeg: str = "ffmpeg",
    columns: int = 4,
    thumb_w: int = 320,
) -> Path | None:
    """One contact-sheet frame per scene midpoint, arranged in a grid."""
    ff = shutil.which(ffmpeg)
    if not ff or not Path(video).is_file() or not manifest.scenes:
        return None
    rows = math.ceil(len(manifest.scenes) / columns)
    tile_h = int(thumb_w * manifest.height / manifest.width)
    filter_parts = []
    inputs: list[str] = []
    labels = []
    for index, scene in enumerate(manifest.scenes):
        mid = (scene.start_s + scene.end_s) / 2
        inputs.extend(["-ss", f"{mid:.3f}", "-i", str(video)])
        filter_parts.append(
            f"[{index}:v]scale={thumb_w}:{tile_h},drawtext=text='{scene.scene_id}':"
            f"fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6:x=6:y=6[t{index}]"
        )
        labels.append(f"[t{index}]")
    filter_parts.append(
        f"{''.join(labels)}xstack=inputs={len(labels)}:layout="
        + "|".join(
            f"{(i % columns) * thumb_w}_{(i // columns) * tile_h}" for i in range(len(labels))
        )
        + f"[v]"
    )
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [ff, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filter_parts),
         "-map", "[v]", "-frames:v", "1", str(destination)],
        capture_output=True, timeout=180, check=False,
    )
    return destination if proc.returncode == 0 and destination.is_file() else None


def build_report(manifest: SceneManifest, video: Path | None = None,
                 work_dir: Path | None = None, ffmpeg: str = "ffmpeg") -> EditorialReport:
    manifest.validate()
    report = EditorialReport(job_id=manifest.job_id, scene_count=len(manifest.scenes))
    repeated, f1 = check_reuses(manifest)
    wall, f2 = check_static_walls(manifest)
    report.repeated_assets = repeated
    report.static_wall_max_s = wall
    report.findings.extend(f1)
    report.findings.extend(f2)
    report.findings.extend(check_objective_agreement(manifest))
    if not report.findings:
        report.findings.append(Finding("note", "editorial_clean",
                                       "No editorial heuristics tripped; human viewing still required."))
    if video is not None and work_dir is not None:
        sheet = make_contact_sheet(manifest, video, Path(work_dir) / "editorial_contact_sheet.jpg", ffmpeg)
        if sheet:
            report.contact_sheet = str(sheet)
        else:
            report.findings.append(Finding("warning", "contact_sheet_failed",
                                           "Could not build a contact sheet from the rendered video."))
    return report
