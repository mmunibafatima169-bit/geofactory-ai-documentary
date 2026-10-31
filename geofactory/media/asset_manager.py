"""Rights-aware registration for explicitly supplied local media."""

from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import json
import logging
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.wikimedia import WikimediaError, request_bytes, request_json

ALLOWED_LICENSES = {
    "CC0-1.0",
    "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0",
    "CC-BY-SA-2.0", "CC-BY-SA-3.0", "CC-BY-SA-4.0",
    "Public Domain",
}
PLATFORM_LICENSES = {
    "Pexels License": "https://www.pexels.com/license/",
    "Pixabay Content License": "https://pixabay.com/service/license-summary/",
}
ALLOWED_MEDIA_LICENSES = ALLOWED_LICENSES | set(PLATFORM_LICENSES)
logger = logging.getLogger(__name__)
_provider_request_lock = threading.Lock()
_provider_last_request = 0.0
MAX_STOCK_VIDEO_BYTES = 250 * 1024 * 1024


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _plain_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    parser.feed(html.unescape(value))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


class AssetRightsError(ValueError):
    """Raised when an asset's reuse rights cannot be established."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _has_image_signature(path: Path) -> bool:
    with path.open("rb") as stream:
        header = stream.read(12)
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix == ".webp":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    if suffix == ".bmp":
        return header.startswith(b"BM")
    return False


def _extract_metadata(info: dict[str, object], key: str) -> str:
    metadata = info.get("extmetadata")
    if not isinstance(metadata, dict):
        return ""
    item = metadata.get(key)
    if isinstance(item, dict):
        return _plain_text(item.get("value"))
    return _plain_text(item)


def _verified_commons_license(info: dict[str, object]) -> tuple[str, str]:
    short_name = _extract_metadata(info, "LicenseShortName")
    license_url = _extract_metadata(info, "LicenseUrl")
    parsed = urlparse(license_url)
    if parsed.scheme == "http" and parsed.hostname == "creativecommons.org":
        license_url = parsed._replace(scheme="https").geturl()
        parsed = urlparse(license_url)
    if parsed.scheme != "https" or parsed.hostname != "creativecommons.org":
        raise AssetRightsError("Commons record has no verifiable Creative Commons licence URL.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise AssetRightsError("Commons licence URL has an invalid authority.")
    normalized = re.sub(r"\s+", " ", short_name).strip().upper()
    match = re.fullmatch(r"CC BY(-SA)? ([234])\.0", normalized)
    if match:
        license_id = f"CC-BY{'-SA' if match.group(1) else ''}-{match.group(2)}.0"
        expected_path = (
            f"/licenses/{'by-sa' if match.group(1) else 'by'}/{match.group(2)}.0"
        )
        if parsed.path.rstrip("/") not in {expected_path, f"{expected_path}/deed.en"}:
            raise AssetRightsError("Commons licence name and licence URL do not match.")
        return license_id, f"https://creativecommons.org{expected_path}/"
    if normalized in {"CC0", "CC0 1.0", "CC0 1.0 UNIVERSAL"}:
        if parsed.path.rstrip("/") not in {
            "/publicdomain/zero/1.0",
            "/publicdomain/zero/1.0/deed.en",
        }:
            raise AssetRightsError("Commons CC0 licence URL is inconsistent.")
        return "CC0-1.0", "https://creativecommons.org/publicdomain/zero/1.0/"
    if normalized.startswith("PUBLIC DOMAIN"):
        if parsed.path.rstrip("/") not in {
            "/publicdomain/mark/1.0",
            "/publicdomain/mark/1.0/deed.en",
        }:
            raise AssetRightsError("Commons public-domain mark URL is missing or unrecognized.")
        return "Public Domain", "https://creativecommons.org/publicdomain/mark/1.0/"
    raise AssetRightsError(
        f"Commons licence {short_name or '(missing)'} is not approved for commercial reuse."
    )


def register_asset(
    db: Database,
    job_id: str,
    file_path: Path,
    origin_url: str,
    creator: str,
    licence: str,
    attribution: str,
    commercial_use: bool,
    *,
    title: str = "",
    publisher: str = "Owner-provided source",
    licence_url: str = "",
) -> str:
    if file_path.is_symlink():
        raise AssetRightsError("Asset must not be a symbolic link.")
    path = file_path.resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        raise AssetRightsError("Asset must be a regular, non-symlink file.")
    if not _has_image_signature(path):
        raise AssetRightsError("Asset extension and image file signature do not match.")
    if licence not in ALLOWED_LICENSES:
        raise AssetRightsError(
            f"Licence {licence!r} is not in the accepted reuse list; unknown rights are rejected."
        )
    if not commercial_use:
        raise AssetRightsError("Asset is not cleared for commercial use.")
    parsed = urlparse(origin_url)
    if (
        parsed.scheme != "https" or not parsed.netloc
        or parsed.username or parsed.password
    ):
        raise AssetRightsError("Asset origin must be a valid HTTPS URL.")
    if licence_url:
        parsed_licence = urlparse(licence_url)
        if (
            parsed_licence.scheme != "https" or not parsed_licence.netloc
            or parsed_licence.username or parsed_licence.password
        ):
            raise AssetRightsError("Asset licence URL must be a valid HTTPS URL.")
    if not creator.strip() or not attribution.strip():
        raise AssetRightsError("Creator and attribution text are required.")
    asset_id = f"ast-{uuid.uuid4().hex[:12]}"
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO assets
               (id, job_id, title, publisher, path, origin_url, creator, licence,
                licence_url, attribution, commercial_use, file_sha256, retrieved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (
                asset_id, job_id, title.strip() or path.stem,
                publisher.strip() or "Owner-provided source", str(path),
                origin_url, creator, licence, licence_url, attribution,
                sha256_file(path), datetime.now(timezone.utc).isoformat(),
            ),
        )
    return asset_id


def register_music_asset(
    db: Database,
    job_id: str,
    file_path: Path,
    origin_url: str,
    creator: str,
    licence: str,
    attribution: str,
    commercial_use: bool,
    *,
    title: str = "",
    publisher: str = "Owner-provided music",
    licence_url: str = "",
) -> str:
    """Register one owner-downloaded music file after its reuse terms are checked."""
    if file_path.is_symlink():
        raise AssetRightsError("Music asset must not be a symbolic link.")
    path = file_path.resolve(strict=True)
    if (
        not path.is_file()
        or path.suffix.lower() not in {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}
        or path.stat().st_size == 0
    ):
        raise AssetRightsError("Music must be a non-empty supported audio file.")
    if licence not in ALLOWED_MEDIA_LICENSES:
        raise AssetRightsError(
            f"Music licence {licence!r} is not approved; unknown rights are rejected."
        )
    if not commercial_use:
        raise AssetRightsError("Music is not cleared for commercial use.")
    parsed = urlparse(origin_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise AssetRightsError("Music origin must be a valid HTTPS URL.")
    if not creator.strip() or not attribution.strip():
        raise AssetRightsError("Music creator and attribution text are required.")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise AssetRightsError("FFprobe is required to validate a music file.")
    probe = subprocess.run(
        [
            ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
            "stream=codec_type", "-of", "json", str(path),
        ],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if probe.returncode:
        raise AssetRightsError("FFprobe could not validate the supplied music file.")
    try:
        streams = json.loads(probe.stdout).get("streams", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise AssetRightsError("FFprobe returned invalid music metadata.") from exc
    if not streams or streams[0].get("codec_type") != "audio":
        raise AssetRightsError("Supplied music file has no readable audio stream.")
    asset_id = f"ast-{uuid.uuid4().hex[:12]}"
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO assets
               (id, job_id, title, publisher, path, origin_url, creator, licence,
                licence_url, attribution, commercial_use, file_sha256, retrieved_at,
                media_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'audio')""",
            (
                asset_id, job_id, title.strip() or path.stem,
                publisher.strip() or "Owner-provided music", str(path),
                origin_url, creator, licence,
                licence_url or PLATFORM_LICENSES.get(licence, ""),
                attribution, sha256_file(path), datetime.now(timezone.utc).isoformat(),
            ),
        )
    return asset_id


def _provider_json(
    url: str, *, provider: str, allowed_host: str, headers: dict[str, str] | None = None
) -> dict[str, object]:
    global _provider_last_request
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != allowed_host:
        raise AssetRightsError(f"{provider} API URL is not on its approved HTTPS host.")
    with _provider_request_lock:
        wait = 1.0 - (time.monotonic() - _provider_last_request)
        if wait > 0:
            time.sleep(wait)
        _provider_last_request = time.monotonic()
    request = Request(
        url,
        headers={"User-Agent": "GeoFactory/1.0 (documentary asset research)", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=30) as response:
            final_url = urlparse(response.geturl())
            if final_url.scheme != "https" or final_url.hostname != allowed_host:
                raise AssetRightsError(f"{provider} API redirected outside its approved host.")
            body = response.read(5 * 1024 * 1024 + 1)
            if len(body) > 5 * 1024 * 1024:
                raise AssetRightsError(f"{provider} API response exceeded 5 MiB.")
    except HTTPError as exc:
        raise AssetRightsError(
            f"{provider} API returned HTTP {exc.code}; check the key, quota, and API access."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise AssetRightsError(f"{provider} API request failed ({type(exc).__name__}).") from exc
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetRightsError(f"{provider} API returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise AssetRightsError(f"{provider} API returned an unexpected response.")
    return data


def _download_stock_video(
    url: str, destination_dir: Path, *, allowed_hosts: set[str], provider: str
) -> tuple[Path, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise AssetRightsError(f"{provider} video URL is not on an approved HTTPS media host.")
    request = Request(url, headers={"User-Agent": "GeoFactory/1.0"})
    try:
        with urlopen(request, timeout=180) as response:
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname not in allowed_hosts:
                raise AssetRightsError(
                    f"{provider} media download redirected outside its approved host."
                )
            content_type = response.headers.get_content_type().lower()
            if content_type != "video/mp4":
                raise AssetRightsError(
                    f"{provider} returned {content_type or 'unknown content'}, not MP4 video."
                )
            declared_size = response.headers.get("Content-Length")
            if declared_size:
                try:
                    if int(declared_size) > MAX_STOCK_VIDEO_BYTES:
                        raise AssetRightsError(f"{provider} video exceeds the 250 MiB limit.")
                except ValueError:
                    raise AssetRightsError(f"{provider} returned an invalid content length.")
            body = bytearray()
            while block := response.read(1024 * 1024):
                body.extend(block)
                if len(body) > MAX_STOCK_VIDEO_BYTES:
                    raise AssetRightsError(f"{provider} video exceeds the 250 MiB limit.")
    except HTTPError as exc:
        raise AssetRightsError(f"{provider} video download returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise AssetRightsError(
            f"{provider} video download failed ({type(exc).__name__})."
        ) from exc
    if len(body) < 12 or body[4:8] != b"ftyp":
        raise AssetRightsError(f"{provider} response is not a valid MP4 file.")
    digest = hashlib.sha256(body).hexdigest()
    destination_dir.mkdir(parents=True, exist_ok=True)
    path = destination_dir / f"{digest}.mp4"
    if path.exists():
        if sha256_file(path) != digest:
            raise AssetRightsError("Refusing to overwrite an unrelated file at the hashed path.")
        return path, digest
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=".geofactory-", suffix=".tmp",
        dir=destination_dir, delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(body)
        stream.flush()
    try:
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return path, digest


def _register_provider_video(
    db: Database,
    job_id: str,
    provider: str,
    title: str,
    creator: str,
    origin_url: str,
    licence: str,
    licence_url: str,
    path: Path,
    digest: str,
) -> dict[str, object]:
    asset_id = f"ast-{uuid.uuid4().hex[:12]}"
    attribution = (
        f'{creator}, "{title}", {provider}, {licence} ({licence_url}), {origin_url}'
    )
    with db.connect() as conn:
        existing = conn.execute(
            "SELECT * FROM assets WHERE job_id = ? AND file_sha256 = ? AND publisher = ?",
            (job_id, digest, provider),
        ).fetchone()
        if existing:
            return dict(existing)
        conn.execute(
            """INSERT INTO assets
               (id, job_id, title, publisher, path, origin_url, creator, licence,
                licence_url, attribution, commercial_use, file_sha256, retrieved_at,
                media_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'video')""",
            (
                asset_id, job_id, title, provider, str(path), origin_url, creator,
                licence, licence_url, attribution, digest,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return dict(conn.execute(
            "SELECT * FROM assets WHERE id = ?", (asset_id,)
        ).fetchone())


def _validate_mp4(path: Path, ffprobe_name: str) -> None:
    ffprobe = shutil.which(ffprobe_name)
    if not ffprobe:
        raise AssetRightsError(f"FFprobe executable not found: {ffprobe_name}")
    result = subprocess.run(
        [
            ffprobe, "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode:
        raise AssetRightsError("Downloaded stock clip failed FFprobe validation.")
    try:
        parsed = json.loads(result.stdout)
        streams = parsed.get("streams", [])
        duration = float(parsed.get("format", {}).get("duration", 0))
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
        raise AssetRightsError("FFprobe returned invalid stock-video metadata.") from exc
    if (
        duration <= 0
        or not any(
            stream.get("codec_type") == "video"
            and int(stream.get("width", 0)) > 0
            and int(stream.get("height", 0)) > 0
            for stream in streams if isinstance(stream, dict)
        )
    ):
        raise AssetRightsError("Downloaded stock clip has no valid video stream.")


def search_and_download_stock_videos(
    db: Database,
    job_id: str,
    query: str,
    destination_dir: Path,
    config: FactoryConfig,
    *,
    provider: str,
    limit: int = 5,
    max_downloads: int = 2,
) -> dict[str, object]:
    """Search and fetch MP4 stock clips through official Pexels/Pixabay video APIs."""
    query = query.strip()
    if not query or len(query) > 200:
        raise AssetRightsError("Stock-video query must contain 1-200 characters.")
    if not 1 <= limit <= 10 or not 1 <= max_downloads <= 5:
        raise AssetRightsError("Stock-video limits must be 1-10 results and 1-5 downloads.")
    if provider not in {"pexels", "pixabay"}:
        raise AssetRightsError("Provider must be 'pexels' or 'pixabay'.")
    key = getattr(config, f"{provider}_api_key")
    if not key:
        raise AssetRightsError(
            f"{provider.title()} API key is not configured in ignored config.json."
        )
    if provider == "pexels":
        api_url = "https://api.pexels.com/videos/search?" + urlencode({
            "query": query, "per_page": limit, "orientation": "landscape",
        })
        data = _provider_json(
            api_url, provider="Pexels", allowed_host="api.pexels.com",
            headers={"Authorization": key},
        )
        candidates = data.get("videos", [])
        license_name = "Pexels License"
        license_url = PLATFORM_LICENSES[license_name]
        hosts = {"videos.pexels.com"}
    else:
        api_url = "https://pixabay.com/api/videos/?" + urlencode({
            "key": key, "q": query, "per_page": limit, "safesearch": "true",
        })
        data = _provider_json(
            api_url, provider="Pixabay", allowed_host="pixabay.com"
        )
        candidates = data.get("hits", [])
        license_name = "Pixabay Content License"
        license_url = PLATFORM_LICENSES[license_name]
        hosts = {"cdn.pixabay.com"}
    if not isinstance(candidates, list):
        raise AssetRightsError(f"{provider.title()} API omitted its video result list.")
    registered: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if provider == "pexels":
            files = candidate.get("video_files", [])
            if not isinstance(files, list):
                rejected.append({"title": "Untitled video", "reason": "Missing video files."})
                continue
            choices = [
                item for item in files
                if isinstance(item, dict)
                and item.get("file_type") == "video/mp4"
                and isinstance(item.get("link"), str)
                and isinstance(item.get("width"), int)
                and 0 < item["width"] <= 1920
            ]
            selected = max(choices, key=lambda item: int(item.get("width", 0)), default=None)
            origin_url = candidate.get("url")
            creator_data = candidate.get("user", {})
            creator = str(creator_data.get("name", "") if isinstance(creator_data, dict) else "")
            title = str(candidate.get("id", "Pexels stock video"))
            download_url = selected.get("link") if selected else None
        else:
            video_set = candidate.get("videos", {})
            selected = video_set.get("large") if isinstance(video_set, dict) else None
            if not isinstance(selected, dict) or not selected.get("url"):
                selected = video_set.get("medium") if isinstance(video_set, dict) else None
            origin_url = candidate.get("pageURL")
            creator = str(candidate.get("user", ""))
            title = str(candidate.get("tags", "Pixabay stock video"))
            download_url = selected.get("url") if isinstance(selected, dict) else None
        if (
            not isinstance(origin_url, str)
            or urlparse(origin_url).scheme != "https"
            or (
                urlparse(origin_url).hostname not in {"pexels.com", "www.pexels.com"}
                if provider == "pexels"
                else urlparse(origin_url).hostname not in {"pixabay.com", "www.pixabay.com"}
            )
            or not isinstance(download_url, str)
            or not creator.strip()
        ):
            rejected.append({"title": title, "reason": "Missing creator, source page, or MP4 URL."})
            continue
        try:
            path, digest = _download_stock_video(
                download_url, destination_dir, allowed_hosts=hosts,
                provider=provider.title(),
            )
            _validate_mp4(path, config.ffprobe)
            registered.append(_register_provider_video(
                db, job_id, provider.title(), title, creator, origin_url,
                license_name, license_url, path, digest,
            ))
        except (AssetRightsError, OSError) as exc:
            rejected.append({"title": title, "reason": str(exc)})
        if len(registered) >= max_downloads:
            break
    return {"assets": registered, "rejected": rejected}


def search_and_download_commons(
    db: Database,
    job_id: str,
    query: str,
    destination_dir: Path,
    *,
    limit: int = 8,
    max_downloads: int = 3,
) -> dict[str, object]:
    """Find Commons files, reject incompatible terms, then download verified images."""
    query = query.strip()
    if not query or len(query) > 250:
        raise AssetRightsError("Commons query must contain 1-250 characters.")
    if not 1 <= limit <= 20 or not 1 <= max_downloads <= 5:
        raise AssetRightsError("Commons limits must be 1-20 results and 1-5 downloads.")
    try:
        response = request_json(
            "commons",
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": 6,
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size|mime",
                "iiurlwidth": 1600,
                "format": "json",
                "formatversion": 2,
            },
        )
    except WikimediaError as exc:
        raise AssetRightsError(str(exc)) from exc
    query_data = response.get("query")
    pages = query_data.get("pages", []) if isinstance(query_data, dict) else []
    if not isinstance(pages, list):
        raise AssetRightsError("Commons API returned an invalid page list.")

    destination_dir.mkdir(parents=True, exist_ok=True)
    registered: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = []
    access_time = datetime.now(timezone.utc).isoformat()
    for page in pages:
        if not isinstance(page, dict):
            continue
        raw_title = page.get("title")
        title = raw_title.removeprefix("File:") if isinstance(raw_title, str) else ""
        imageinfo = page.get("imageinfo")
        if not title or not isinstance(imageinfo, list) or not imageinfo or not isinstance(imageinfo[0], dict):
            rejected.append({"title": str(raw_title or "(untitled)"), "reason": "Missing image metadata."})
            continue
        info = imageinfo[0]
        try:
            license_id, license_url = _verified_commons_license(info)
        except AssetRightsError as exc:
            rejected.append({"title": title, "reason": str(exc)})
            continue

        creator = (
            _extract_metadata(info, "Artist")
            or _extract_metadata(info, "Creator")
            or "Not stated in Commons metadata"
        )
        origin_url = info.get("descriptionurl")
        download_url = info.get("thumburl") or info.get("url")
        if not isinstance(origin_url, str) or not isinstance(download_url, str):
            rejected.append({"title": title, "reason": "Commons record has no source or image URL."})
            continue
        parsed_origin = urlparse(origin_url)
        if parsed_origin.scheme != "https" or parsed_origin.hostname != "commons.wikimedia.org":
            rejected.append({"title": title, "reason": "Description page is not on Wikimedia Commons."})
            continue
        declared_size = info.get("thumbsize", info.get("size", 0))
        if isinstance(declared_size, int) and declared_size > 25 * 1024 * 1024:
            rejected.append({"title": title, "reason": "Image exceeds the 25 MiB download limit."})
            continue
        try:
            payload = request_bytes(
                download_url, max_bytes=25 * 1024 * 1024, media_download=True
            )
        except WikimediaError as exc:
            rejected.append({"title": title, "reason": str(exc)})
            continue
        extension_by_type = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        extension = extension_by_type.get(payload.content_type)
        if not extension:
            rejected.append(
                {"title": title, "reason": f"Unsupported image media type: {payload.content_type}."}
            )
            continue
        attribution = (
            f"{creator}, “{title},” Wikimedia Commons, {license_id} "
            f"({license_url}), {origin_url}"
        )
        digest = hashlib.sha256(payload.body).hexdigest()
        final_path = destination_dir / f"{digest}{extension}"
        temporary_path: Path | None = None
        check_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".geofactory-", suffix=".tmp",
                dir=destination_dir, delete=False,
            ) as output:
                temporary_path = Path(output.name)
                output.write(payload.body)
                output.flush()
            check_path = temporary_path.with_suffix(extension)
            temporary_path.replace(check_path)
            temporary_path = None
            if not _has_image_signature(check_path):
                check_path.unlink(missing_ok=True)
                check_path = None
                rejected.append({"title": title, "reason": "Downloaded bytes do not match an allowed image signature."})
                continue
            with db.connect() as conn:
                existing = conn.execute(
                    "SELECT * FROM assets WHERE job_id = ? AND file_sha256 = ? LIMIT 1",
                    (job_id, digest),
                ).fetchone()
                if existing:
                    check_path.unlink(missing_ok=True)
                    check_path = None
                    registered.append(dict(existing))
                    if len(registered) >= max_downloads:
                        break
                    continue
                if final_path.exists() and sha256_file(final_path) != digest:
                    raise AssetRightsError("Refusing to overwrite an unrelated file at the content-addressed path.")
                if check_path != final_path:
                    check_path.replace(final_path)
                    check_path = None
                asset_id = f"ast-{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """INSERT INTO assets
                       (id, job_id, title, publisher, path, origin_url, creator, licence,
                        licence_url, attribution, commercial_use, file_sha256, retrieved_at)
                       VALUES (?, ?, ?, 'Wikimedia Commons', ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                    (
                        asset_id, job_id, title, str(final_path), origin_url, creator,
                        license_id, license_url, attribution, digest, access_time,
                    ),
                )
                record = conn.execute(
                    "SELECT * FROM assets WHERE id = ?", (asset_id,)
                ).fetchone()
                registered.append(dict(record))
        except OSError as exc:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            if check_path:
                check_path.unlink(missing_ok=True)
            raise AssetRightsError(f"Could not store downloaded Commons image: {exc}") from exc
        except Exception:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            if check_path:
                check_path.unlink(missing_ok=True)
            raise
        if len(registered) >= max_downloads:
            break
    return {"assets": registered, "rejected": rejected}


def export_asset_ledger(db: Database, job_id: str, destination: Path) -> list[dict[str, object]]:
    with db.connect() as conn:
        records = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM assets WHERE job_id = ? ORDER BY id", (job_id,)
            )
        ]
    for record in records:
        record.pop("job_id", None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    import json

    destination.write_text(
        json.dumps({"assets": records}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return records


def write_attribution_report(records: list[dict[str, object]], destination: Path) -> None:
    lines = ["# Media attribution", ""]
    if not records:
        lines.append("No external assets are included.")
    for record in records:
        lines.append(
            f"- **{record.get('media_type', 'image').title()}**: {record['attribution']} — "
            f"[licence]({record.get('licence_url') or record['licence']}) — "
            f"[origin]({record['origin_url']})"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
