#!/usr/bin/env python3
"""Probe, rights-check and rank the two Venice sample footage assets."""

from __future__ import annotations

import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from geofactory.studio.asset_selector import (  # noqa: E402
    VisualAssetCandidate, duplicate_shots, probe_asset, score_candidate,
    write_asset_selection,
)

PUBLIC = REPO / "studio/remotion/public/footage"
FFMPEG = str(REPO / ".tools/ffmpeg")
FFPROBE = str(REPO / ".tools/ffprobe")
TODAY = date.today().isoformat()
EXPECTED_BYTES = {
    "commons-gondolas-2015": 31_249_765,
    "commons-grand-canal-1896": 78_822_612,
}
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


def download_if_missing(asset: VisualAssetCandidate) -> None:
    path = Path(asset.local_path)
    if path.is_file() and path.stat().st_size == EXPECTED_BYTES[asset.asset_id]:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(
        asset.download_url,
        headers={"User-Agent": "GeoFactory/1.0 documentary asset fetch"},
    )
    total = 0
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as handle:
        declared = int(response.headers.get("Content-Length") or 0)
        if declared and declared > MAX_DOWNLOAD_BYTES:
            raise RuntimeError(f"Refusing oversized asset ({declared} bytes): {asset.asset_id}")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise RuntimeError(f"Asset exceeded {MAX_DOWNLOAD_BYTES} bytes: {asset.asset_id}")
            handle.write(chunk)
    expected = EXPECTED_BYTES[asset.asset_id]
    if total != expected:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Size mismatch for {asset.asset_id}: expected {expected}, got {total}")
    partial.replace(path)


def main() -> int:
    assets = [
        VisualAssetCandidate(
            asset_id="commons-gondolas-2015",
            title="Gondolas in Venice",
            description="Real modern footage of gondolas moving through Venice canals; city built on water.",
            media_type="video",
            source_page="https://commons.wikimedia.org/wiki/File:Gondolas_in_Venice.webm",
            download_url="https://upload.wikimedia.org/wikipedia/commons/4/46/Gondolas_in_Venice.webm",
            creator="Amada44",
            licence="CC BY-SA 3.0",
            licence_url="https://creativecommons.org/licenses/by-sa/3.0/",
            accessed_at=TODAY,
            local_path=str(PUBLIC / "gondolas.webm"),
            tags=["venice", "gondola", "canal", "water", "city"],
        ),
        VisualAssetCandidate(
            asset_id="commons-grand-canal-1896",
            title="Venise, Panorama du Grand Canal, 1896",
            description="Historical archival moving image of Venice's Grand Canal filmed in 1896.",
            media_type="video",
            source_page="https://commons.wikimedia.org/wiki/File:Venise_Panorama_du_Grand_Canal_1896.webm",
            download_url="https://upload.wikimedia.org/wikipedia/commons/e/e8/Venise_Panorama_du_Grand_Canal_1896.webm",
            creator="Alexandre Promio",
            licence="Public domain",
            licence_url="https://creativecommons.org/publicdomain/mark/1.0/",
            accessed_at=TODAY,
            local_path=str(PUBLIC / "venice-1896.webm"),
            tags=["venice", "grand canal", "historical", "archive", "1896"],
        ),
    ]
    for asset in assets:
        download_if_missing(asset)
        probe_asset(asset, FFPROBE)
    scores = [
        score_candidate(
            "Venice is a city built on water, with canals and a long historical record.",
            asset,
            previous_titles=[a.title for a in assets[:index]],
        )
        for index, asset in enumerate(assets)
    ]
    duplicates = duplicate_shots(assets, FFMPEG)
    if duplicates:
        raise SystemExit(f"Duplicate footage detected: {duplicates}")
    output = REPO / "studio/remotion/out/asset_selection.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_asset_selection(output, assets, scores)
    print(f"Asset ledger: {output}")
    for asset, score in zip(assets, scores, strict=True):
        print(
            f"{asset.asset_id}: {asset.width}x{asset.height} {asset.duration_s:.1f}s "
            f"sha256={asset.sha256[:12]} score={score.overall}/100 {asset.licence}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
