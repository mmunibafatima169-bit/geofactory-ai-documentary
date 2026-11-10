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
import re
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
    columns: int = 3,
    thumb_w: int = 480,
) -> Path | None:
    """One labelled frame per scene midpoint, arranged in a grid.

    FFmpeg only extracts frames (no `drawtext`, which many static builds omit);
    Pillow composes the grid and burns the scene labels.
    """
    ff = shutil.which(ffmpeg) or (ffmpeg if Path(ffmpeg).exists() else None)
    if not ff or not Path(video).is_file() or not manifest.scenes:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    work = destination.parent / f".{destination.stem}.frames"
    work.mkdir(parents=True, exist_ok=True)

    tile_h = int(thumb_w * manifest.height / manifest.width)
    label_h = 34
    frames: list[tuple[Path, str]] = []
    for index, scene in enumerate(manifest.scenes):
        mid = (scene.start_s + scene.end_s) / 2
        shot = work / f"{index:02d}.jpg"
        proc = subprocess.run(
            [ff, "-y", "-v", "error", "-ss", f"{mid:.3f}", "-i", str(video),
             "-frames:v", "1", "-vf", f"scale={thumb_w}:{tile_h}", "-q:v", "4", str(shot)],
            capture_output=True, timeout=120, check=False,
        )
        if proc.returncode == 0 and shot.is_file():
            frames.append((shot, f"{scene.scene_id} · {scene.engine} · {scene.visual_objective}"))
    if not frames:
        return None

    rows = math.ceil(len(frames) / columns)
    sheet = Image.new("RGB", (columns * thumb_w, rows * (tile_h + label_h)), (10, 16, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    for index, (shot, caption) in enumerate(frames):
        col, row = index % columns, index // columns
        x, y = col * thumb_w, row * (tile_h + label_h)
        with Image.open(shot) as tile:
            sheet.paste(tile.convert("RGB"), (x, y))
        draw.rectangle([x, y + tile_h, x + thumb_w, y + tile_h + label_h], fill=(18, 28, 40))
        draw.text((x + 10, y + tile_h + 9), caption, font=font, fill=(245, 241, 232))
    sheet.save(destination, quality=90)
    for shot, _ in frames:
        shot.unlink(missing_ok=True)
    work.rmdir()
    return destination if destination.is_file() else None


def _timestamp_s(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def check_subtitles(path: Path, duration: float) -> list[Finding]:
    findings: list[Finding] = []
    if not Path(path).is_file():
        return [Finding("critical", "subtitles_missing", "Expected SRT file is missing.")]
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    cues = re.findall(
        r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n([^\n]+)",
        text,
    )
    if not cues:
        return [Finding("critical", "subtitles_invalid", "No valid SRT cues found.")]
    last_end = 0.0
    for start_raw, end_raw, caption in cues:
        start, end = _timestamp_s(start_raw), _timestamp_s(end_raw)
        if end <= start or start < last_end - 0.02:
            findings.append(Finding("critical", "subtitle_timing_invalid", f"Overlapping/reversed cue: {start_raw} → {end_raw}"))
        if end > duration + 0.25:
            findings.append(Finding("critical", "subtitle_out_of_bounds", f"Cue ends after video: {end:.2f}s > {duration:.2f}s"))
        if len(caption) > 92:
            findings.append(Finding("warning", "subtitle_too_long", f"Cue is {len(caption)} characters: {caption[:45]}…"))
        last_end = end
    return findings


def check_rendered_video(video: Path, manifest: SceneManifest, ffmpeg: str, ffprobe: str | None = None) -> tuple[float, list[Finding]]:
    findings: list[Finding] = []
    video = Path(video)
    if not video.is_file():
        return 0.0, [Finding("critical", "video_missing", f"Rendered video is missing: {video}")]
    probe = ffprobe or (str(Path(ffmpeg).with_name("ffprobe")) if Path(ffmpeg).exists() else "ffprobe")
    proc = subprocess.run(
        [probe, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,r_frame_rate,duration",
         "-of", "json", str(video)], capture_output=True, text=True, timeout=90, check=False,
    )
    if proc.returncode != 0:
        return 0.0, [Finding("critical", "probe_failed", proc.stderr[-250:])]
    info = json.loads(proc.stdout)
    duration = float(info.get("format", {}).get("duration") or 0)
    vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    astream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not vstream or not astream:
        findings.append(Finding("critical", "missing_av_stream", "Final video needs video and audio streams."))
        return duration, findings
    if int(vstream.get("width") or 0) != manifest.width or int(vstream.get("height") or 0) != manifest.height:
        findings.append(Finding("critical", "resolution_mismatch", f"Expected {manifest.width}x{manifest.height}, got {vstream.get('width')}x{vstream.get('height')}"))
    fps_raw = str(vstream.get("r_frame_rate", "0/1"))
    num, den = (float(v) for v in fps_raw.split("/"))
    fps = num / den if den else 0
    if abs(fps - manifest.fps) > 0.01:
        findings.append(Finding("critical", "fps_mismatch", f"Expected {manifest.fps}fps, got {fps:.3f}"))
    audio_duration = float(astream.get("duration") or duration)
    if abs(duration - audio_duration) > 0.25:
        findings.append(Finding("critical", "av_desync", f"Audio/video duration drift is {abs(duration-audio_duration):.3f}s"))

    # Decode once through black/freeze detectors; false positives at authored
    # transitions below 0.5s are ignored by the detector duration thresholds.
    ff = shutil.which(ffmpeg) or (ffmpeg if Path(ffmpeg).exists() else None)
    if ff:
        scan = subprocess.run(
            [ff, "-hide_banner", "-i", str(video), "-an", "-vf",
             "blackdetect=d=0.55:pix_th=0.08,freezedetect=n=-58dB:d=1.8",
             "-f", "null", "-"], capture_output=True, text=True, timeout=300, check=False,
        )
        for match in re.finditer(r"black_start:([0-9.]+).*?black_duration:([0-9.]+)", scan.stderr):
            findings.append(Finding("warning", "black_run", f"Black run at {float(match.group(1)):.2f}s for {float(match.group(2)):.2f}s"))
        freezes = re.findall(r"freeze_start:\s*([0-9.]+)", scan.stderr)
        for start in freezes:
            findings.append(Finding("warning", "frozen_run", f"Potential frozen visual from {float(start):.2f}s; inspect manually."))
        audio = subprocess.run(
            [ff, "-hide_banner", "-i", str(video), "-vn", "-af",
             "silencedetect=n=-45dB:d=1.8,astats=metadata=1:reset=0", "-f", "null", "-"],
            capture_output=True, text=True, timeout=180, check=False,
        )
        for match in re.finditer(r"silence_start:\s*([0-9.]+)", audio.stderr):
            findings.append(Finding("warning", "long_silence", f"Audio silence begins at {float(match.group(1)):.2f}s"))
        peaks = re.findall(r"Peak level dB:\s*(-?[0-9.]+)", audio.stderr)
        if peaks and max(float(p) for p in peaks) > -0.5:
            findings.append(Finding("critical", "audio_clipping_risk", f"Audio peak {max(float(p) for p in peaks):.2f} dBFS"))
    return duration, findings


def build_report(manifest: SceneManifest, video: Path | None = None,
                 work_dir: Path | None = None, ffmpeg: str = "ffmpeg",
                 subtitles: Path | None = None, fact_report: dict | None = None) -> EditorialReport:
    manifest.validate()
    report = EditorialReport(job_id=manifest.job_id, scene_count=len(manifest.scenes))
    repeated, f1 = check_reuses(manifest)
    wall, f2 = check_static_walls(manifest)
    report.repeated_assets = repeated
    report.static_wall_max_s = wall
    report.findings.extend(f1)
    report.findings.extend(f2)
    report.findings.extend(check_objective_agreement(manifest))
    for scene in manifest.scenes:
        for asset in scene.assets:
            if "://" not in asset and not Path(asset).is_file():
                report.findings.append(Finding(
                    "critical", "scene_asset_missing", f"Scene asset is missing: {asset}", scene.scene_id
                ))
    duration = 0.0
    if video is not None:
        duration, rendered_findings = check_rendered_video(Path(video), manifest, ffmpeg)
        report.findings.extend(rendered_findings)
    if subtitles is not None:
        report.findings.extend(check_subtitles(Path(subtitles), duration))
    if fact_report:
        for item in fact_report.get("findings", []):
            if item.get("level") in {"critical", "warning"}:
                report.findings.append(Finding(
                    str(item["level"]), f"fact_{item.get('code', 'finding')}",
                    str(item.get("message", "Factual verification finding")),
                    item.get("claim_id"),
                ))
    if not report.findings:
        report.findings.append(Finding("note", "editorial_clean",
                                       "No editorial heuristics tripped; human viewing still required."))
    if video is not None and work_dir is not None:
        sheet = make_contact_sheet(manifest, Path(video), Path(work_dir) / "editorial_contact_sheet.jpg", ffmpeg)
        if sheet:
            report.contact_sheet = str(sheet)
        else:
            report.findings.append(Finding("warning", "contact_sheet_failed",
                                           "Could not build a contact sheet from the rendered video."))
    return report
