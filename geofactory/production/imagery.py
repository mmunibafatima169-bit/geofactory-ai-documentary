"""Rights-aware STAC satellite acquisition with bounded HTTPS downloads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request


class ImageryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageryProvider:
    name: str
    search_url: str
    collections: tuple[str, ...]
    allowed_download_hosts: tuple[str, ...]
    licence: str
    licence_url: str
    attribution: str

    def validate(self) -> None:
        parsed = urlparse(self.search_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ImageryError("STAC search URL must use HTTPS")
        if not self.collections or not self.allowed_download_hosts:
            raise ImageryError("Collections and explicit download allowlist are required")
        if not self.licence.strip() or not self.attribution.strip() or urlparse(self.licence_url).scheme != "https":
            raise ImageryError("Provider licence and attribution must be recorded")


@dataclass(frozen=True)
class ImagerySelection:
    provider: str
    item_id: str
    collection: str
    acquired_at: str
    cloud_cover: float | None
    bbox: tuple[float, ...]
    assets: dict[str, str]
    licence: str
    attribution: str
    rights_review_required: bool = True


class STACClient:
    """Synchronous STAC client with injectable transport for deterministic tests."""

    def __init__(self, provider: ImageryProvider, transport: Callable | None = None, max_response_bytes: int = 8 * 1024 * 1024):
        provider.validate()
        self.provider = provider
        self.transport = transport
        self.max_response_bytes = max_response_bytes

    def _request(self, url: str, payload: dict | None = None):
        if self.transport:
            return self.transport(url, payload)
        from urllib.request import urlopen
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(url, data=body, headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "GeoFactory/0.1"})
        return urlopen(request, timeout=45)

    def search(self, bbox: tuple[float, float, float, float], datetime_range: str, max_cloud_cover: float = 20.0, limit: int = 10) -> list[ImagerySelection]:
        if len(bbox) != 4 or not 0 <= max_cloud_cover <= 100 or not 1 <= limit <= 100:
            raise ImageryError("Invalid STAC search constraints")
        payload = {"bbox": list(bbox), "datetime": datetime_range, "collections": list(self.provider.collections), "limit": limit, "query": {"eo:cloud_cover": {"lte": max_cloud_cover}}}
        with self._request(self.provider.search_url, payload) as response:
            raw = response.read(self.max_response_bytes + 1)
        if len(raw) > self.max_response_bytes:
            raise ImageryError("STAC response exceeds configured bound")
        data = json.loads(raw)
        selections = []
        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            assets = {name: asset.get("href", "") for name, asset in feature.get("assets", {}).items() if isinstance(asset, dict)}
            selections.append(ImagerySelection(self.provider.name, str(feature.get("id", "")), str(feature.get("collection", "")), str(properties.get("datetime", "")), properties.get("eo:cloud_cover"), tuple(feature.get("bbox", bbox)), assets, self.provider.licence, self.provider.attribution))
        return sorted(selections, key=lambda item: (float("inf") if item.cloud_cover is None else item.cloud_cover, item.acquired_at), reverse=False)

    def download_asset(self, selection: ImagerySelection, asset_role: str, destination: Path, max_bytes: int = 250 * 1024 * 1024) -> dict:
        url = selection.assets.get(asset_role)
        if not url:
            raise ImageryError(f"Missing asset role: {asset_role}")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in self.provider.allowed_download_hosts:
            raise ImageryError("Asset URL is outside the provider's explicit HTTPS allowlist")
        with self._request(url) as response:
            body = response.read(max_bytes + 1)
        if not body or len(body) > max_bytes:
            raise ImageryError("Downloaded asset is empty or exceeds configured bound")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(body)
        temporary.replace(destination)
        return {"path": str(destination), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "item_id": selection.item_id, "asset_role": asset_role, "source_url": url, "licence": selection.licence, "attribution": selection.attribution, "rights_review_required": True}
