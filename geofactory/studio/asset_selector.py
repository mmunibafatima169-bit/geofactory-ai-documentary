"""Licensed visual-asset ranking and duplicate/technical checks.

Scores candidates against the narration beat, not generic aesthetic appeal.
Every accepted asset retains rights/provenance metadata and a file hash. The
selector never treats a provider's search rank as editorial relevance.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_LICENCES = {
    "CC0-1.0", "CC BY 3.0", "CC BY-SA 3.0", "CC BY 4.0", "CC BY-SA 4.0",
    "Public domain", "Public Domain",
}

STOP = {"the", "a", "an", "of", "to", "and", "in", "on", "is", "it", "that", "with", "this", "its"}


class AssetSelectionError(ValueError):
    pass


@dataclass
class VisualAssetCandidate:
    asset_id: str
    title: str
    description: str
    media_type: str
    source_page: str
    download_url: str
    creator: str
    licence: str
    licence_url: str
    accessed_at: str
    local_path: str = ""
    width: int = 0
    height: int = 0
    duration_s: float = 0.0
    sha256: str = ""
    tags: list[str] = field(default_factory=list)

    def validate_rights(self) -> None:
        for url in (self.source_page, self.download_url, self.licence_url):
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise AssetSelectionError(f"{self.asset_id}: every provenance URL must use HTTPS")
        if self.licence not in ALLOWED_LICENCES:
            raise AssetSelectionError(f"{self.asset_id}: unsupported licence {self.licence!r}")
        if not self.creator.strip():
            raise AssetSelectionError(f"{self.asset_id}: creator/rights attribution missing")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AssetScore:
    asset_id: str
    semantic_relevance: int
    technical_quality: int
    visual_variety: int
    rights_confidence: int
    overall: int
    explanation: str


def _terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in STOP}


def score_candidate(
    narration: str,
    candidate: VisualAssetCandidate,
    *,
    previous_titles: list[str] | None = None,
    target_aspect: float = 16 / 9,
) -> AssetScore:
    candidate.validate_rights()
    need = _terms(narration)
    have = _terms(" ".join([candidate.title, candidate.description, *candidate.tags]))
    overlap = need & have
    semantic = min(100, 25 + 18 * len(overlap)) if overlap else 10

    aspect = candidate.width / candidate.height if candidate.height else 0
    aspect_delta = abs(aspect - target_aspect)
    resolution = min(100, round((candidate.width * candidate.height) / (1920 * 1080) * 100)) if aspect else 0
    technical = max(0, round(0.7 * resolution + 30 * max(0.0, 1 - aspect_delta / target_aspect)))
    if candidate.media_type == "video" and not (2 <= candidate.duration_s <= 120):
        technical = max(0, technical - 30)

    previous = " ".join(previous_titles or [])
    repeated_terms = _terms(previous) & have
    variety = max(20, 100 - 12 * len(repeated_terms))
    rights = 100 if candidate.licence in ALLOWED_LICENCES and candidate.licence_url else 0
    overall = round(semantic * 0.5 + technical * 0.22 + variety * 0.13 + rights * 0.15)
    reason = (
        f"semantic overlap={sorted(overlap) or ['none']}; {candidate.width}x{candidate.height}, "
        f"{candidate.duration_s:.1f}s; aspect delta={aspect_delta:.3f}; "
        f"repeat-term penalty={len(repeated_terms)}; licence={candidate.licence}"
    )
    return AssetScore(candidate.asset_id, semantic, technical, variety, rights, overall, reason)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_asset(candidate: VisualAssetCandidate, ffprobe: str = "ffprobe") -> VisualAssetCandidate:
    path = Path(candidate.local_path)
    if not path.is_file() or path.stat().st_size < 1024:
        raise AssetSelectionError(f"{candidate.asset_id}: downloaded file missing/empty")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=60, check=False,
    )
    if proc.returncode != 0:
        raise AssetSelectionError(f"{candidate.asset_id}: FFprobe failed: {proc.stderr[-250:]}")
    info = json.loads(proc.stdout)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        raise AssetSelectionError(f"{candidate.asset_id}: no video stream")
    candidate.width = int(video.get("width") or 0)
    candidate.height = int(video.get("height") or 0)
    candidate.duration_s = float(info.get("format", {}).get("duration") or 0)
    candidate.sha256 = sha256_file(path)
    return candidate


def frame_signature(path: Path, at_s: float, ffmpeg: str = "ffmpeg") -> str | None:
    """64-byte grayscale signature; exact duplicate shots match after scaling."""
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-ss", f"{at_s:.3f}", "-i", str(path),
         "-frames:v", "1", "-vf", "scale=8:8,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, timeout=60, check=False,
    )
    return hashlib.sha256(proc.stdout).hexdigest() if proc.returncode == 0 and len(proc.stdout) == 64 else None


def duplicate_shots(candidates: list[VisualAssetCandidate], ffmpeg: str = "ffmpeg") -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    duplicates: list[tuple[str, str]] = []
    for asset in candidates:
        if not asset.local_path:
            continue
        signature = frame_signature(Path(asset.local_path), max(0.0, asset.duration_s / 2), ffmpeg)
        if signature and signature in seen:
            duplicates.append((seen[signature], asset.asset_id))
        elif signature:
            seen[signature] = asset.asset_id
    return duplicates


def write_asset_selection(path: Path, assets: list[VisualAssetCandidate], scores: list[AssetScore]) -> None:
    data = {
        "generated_at": date.today().isoformat(),
        "assets": [a.to_dict() for a in assets],
        "scores": [asdict(s) for s in scores],
        "notice": "Scores are editorial heuristics; rights and relevance still require human review.",
    }
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
