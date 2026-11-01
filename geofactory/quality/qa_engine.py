"""Technical, evidence, and rights checks that gate human approval."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.media.asset_manager import ALLOWED_MEDIA_LICENSES, sha256_file
from geofactory.media.map_animation_engine import MapAnimationError, validate_map_scene
from geofactory.media.video_editor import probe_video
from geofactory.media.tts_engine import audio_duration_seconds


TIMESTAMP_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")


def _check(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def validate_srt(path: Path) -> list[str]:
    if not path.is_file():
        return ["Subtitles file is missing."]
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return ["Subtitles file is empty."]
    problems = []
    previous_end_ms = -1
    expected_index = 1
    for block_number, block in enumerate(re.split(r"\n\s*\n", text), 1):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].isdigit() or " --> " not in lines[1]:
            problems.append(f"Subtitle block {block_number} has invalid structure.")
            continue
        if int(lines[0]) != expected_index:
            problems.append(f"Subtitle block {block_number} has a missing or unordered index.")
        expected_index += 1
        start, end = lines[1].split(" --> ", 1)
        match_start, match_end = TIMESTAMP_RE.fullmatch(start), TIMESTAMP_RE.fullmatch(end)
        if not match_start or not match_end:
            problems.append(f"Subtitle block {block_number} has invalid timestamps.")
            continue
        start_ms = _to_ms(match_start.groups())
        end_ms = _to_ms(match_end.groups())
        if start_ms < 0 or end_ms < 0 or end_ms <= start_ms or end_ms - start_ms > 10_000:
            problems.append(f"Subtitle block {block_number} has an invalid duration.")
        if start_ms < previous_end_ms:
            problems.append(f"Subtitle block {block_number} overlaps the previous cue.")
        previous_end_ms = end_ms
        if any(len(line) > 46 for line in lines[2:]):
            problems.append(f"Subtitle block {block_number} has a line over 46 characters.")
    return problems


def _to_ms(parts: tuple[str, ...]) -> int:
    hours, minutes, seconds, millis = (int(part) for part in parts)
    if minutes > 59 or seconds > 59:
        return -1
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def _srt_end_seconds(path: Path) -> float | None:
    if not path.is_file():
        return None
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    if not blocks:
        return None
    lines = blocks[-1].splitlines()
    if len(lines) < 2 or " --> " not in lines[1]:
        return None
    match = TIMESTAMP_RE.fullmatch(lines[1].split(" --> ", 1)[1])
    if not match:
        return None
    return _to_ms(match.groups()) / 1000


def _decode_and_check_audio(config: FactoryConfig, video_path: Path) -> None:
    ffmpeg = shutil.which(config.ffmpeg)
    if not ffmpeg:
        raise RuntimeError(f"FFmpeg executable not found: {config.ffmpeg}")
    try:
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-nostats", "-i", str(video_path),
                "-map", "0:v:0", "-map", "0:a:0", "-af", "volumedetect",
                "-f", "null", "-",
            ],
            capture_output=True, text=True, timeout=1800, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Full video/audio decode exceeded the 30-minute QA timeout.") from exc
    if result.returncode:
        raise RuntimeError(f"Full video/audio decode failed: {result.stderr[-1500:]}")
    peak_match = re.search(
        r"max_volume:\s*(-inf|-?\d+(?:\.\d+)?) dB", result.stderr
    )
    if not peak_match:
        raise RuntimeError("FFmpeg did not report final audio peak levels.")
    peak = float("-inf") if peak_match.group(1) == "-inf" else float(peak_match.group(1))
    if peak <= -55.0:
        raise RuntimeError(f"Rendered narration is silent or nearly silent ({peak:g} dBFS).")
    if peak >= -0.1:
        raise RuntimeError(f"Rendered audio may be clipped (peak {peak:g} dBFS).")


def run_qa(db: Database, job_id: str, config: FactoryConfig) -> dict[str, Any]:
    from geofactory.core.jobs import get_job

    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    checks: list[dict[str, str]] = []
    video_path = package / "final.mp4"
    if not video_path.is_file() or video_path.stat().st_size == 0:
        checks.append(_check("critical", "missing_video", "Final video is missing or empty."))
    else:
        try:
            probe = probe_video(config, video_path)
            streams = probe.get("streams", [])
            video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
            audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
            subtitle_stream = next(
                (stream for stream in streams if stream.get("codec_type") == "subtitle"),
                None,
            )
            if video_stream is None:
                checks.append(_check("critical", "missing_video_stream", "Video has no video stream."))
            if audio_stream is None:
                checks.append(_check("critical", "missing_audio_stream", "Video has no audio stream."))
            if subtitle_stream is None:
                checks.append(_check("critical", "missing_subtitle_stream", "Video has no soft subtitle stream."))
            if video_stream:
                width, height = int(video_stream.get("width", 0)), int(video_stream.get("height", 0))
                if width < 1280 or height < 720:
                    checks.append(_check("critical", "low_resolution", f"Resolution is {width}x{height}; minimum is 1280x720."))
            duration = float(probe.get("format", {}).get("duration", 0))
            if duration < 480 or duration > 900:
                checks.append(_check("critical", "duration_out_of_range", f"Video duration is {duration:.1f}s; target is 480-900s."))
            if audio_stream:
                try:
                    audio_duration = float(audio_stream.get("duration", duration))
                    if abs(duration - audio_duration) > 0.75:
                        checks.append(_check(
                            "critical", "audio_video_desynchronized",
                            f"Video ({duration:.2f}s) and narration ({audio_duration:.2f}s) differ by more than 0.75s.",
                        ))
                except (TypeError, ValueError):
                    checks.append(_check("critical", "audio_duration_invalid", "FFprobe returned an invalid audio stream duration."))
            subtitle_end = _srt_end_seconds(package / "subtitles.srt")
            if subtitle_end is not None and abs(duration - subtitle_end) > 2.0:
                checks.append(_check(
                    "critical", "subtitle_audio_desynchronized",
                    f"Subtitle end ({subtitle_end:.2f}s) differs from video ({duration:.2f}s) by more than 2s.",
                ))
            _decode_and_check_audio(config, video_path)
            checks.append(_check("info", "probe_passed", "FFprobe opened the rendered file. Manual frame/audio review remains required."))
        except (RuntimeError, ValueError, OSError, StopIteration) as exc:
            checks.append(_check("critical", "video_probe_failed", str(exc)))

    subtitle_problems = validate_srt(package / "subtitles.srt")
    for problem in subtitle_problems:
        checks.append(_check("critical", "subtitle_invalid", problem))
    if not subtitle_problems:
        checks.append(_check("info", "subtitles_present", "Subtitle file has valid SRT structure and line-length limits."))

    narration = package / "narration.wav"
    if not narration.is_file() or narration.stat().st_size == 0:
        checks.append(_check("critical", "missing_narration", "Narration audio WAV is missing or empty."))
    manifest_path = package / "narration_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("mode") != "audio":
            checks.append(_check(
                "critical", "narration_not_audio",
                "Narration manifest does not confirm generated speech audio.",
            ))
        elif (
            not narration.is_file()
            or manifest.get("audio_sha256") != sha256_file(narration)
            or manifest.get("narration_text_sha256")
            != sha256_file(package / "narration.txt")
            or manifest.get("subtitles_sha256")
            != sha256_file(package / "subtitles.srt")
        ):
            checks.append(_check(
                "critical", "narration_manifest_mismatch",
                "Narration, source text, or subtitles changed after audio generation.",
            ))
        else:
            measured_duration = audio_duration_seconds(narration, config.ffprobe)
            if abs(measured_duration - float(manifest.get("duration_seconds", 0))) > 0.25:
                checks.append(_check(
                    "critical", "narration_duration_mismatch",
                    "Recorded narration duration differs from FFprobe measurement.",
                ))
    except (OSError, json.JSONDecodeError, TypeError, ValueError, RuntimeError) as exc:
        checks.append(_check("critical", "narration_manifest_invalid", f"Narration manifest is invalid: {exc}"))

    with db.connect() as conn:
        sources = conn.execute("SELECT * FROM sources WHERE job_id = ?", (job_id,)).fetchall()
        claims = conn.execute(
            "SELECT * FROM claims WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        assets = conn.execute("SELECT * FROM assets WHERE job_id = ?", (job_id,)).fetchall()
    known_source_ids = {row["id"] for row in sources}
    try:
        source_ledger = json.loads((package / "source_ledger.json").read_text(encoding="utf-8"))
        source_records = {record["id"]: record for record in source_ledger.get("sources", [])}
        claim_records = {record["id"]: record for record in source_ledger.get("claims", [])}
        if set(source_records) != known_source_ids or set(claim_records) != {row["id"] for row in claims}:
            checks.append(_check("critical", "source_ledger_mismatch", "Source/claim ledger does not match persisted research records."))
        for source in sources:
            if not str(source["licence"]).strip() or source["licence"].casefold() == "unknown":
                checks.append(_check("critical", "source_licence_missing", f"Source {source['id']} has no verified licence record."))
            record = source_records.get(source["id"], {})
            if any(
                record.get(field) != source[field]
                for field in ("title", "url", "publisher", "licence", "licence_url", "evidence")
            ):
                checks.append(_check("critical", "source_ledger_mismatch", f"Source {source['id']} differs from its persisted record."))
        for claim in claims:
            record = claim_records.get(claim["id"], {})
            if (
                record.get("text") != claim["text"]
                or record.get("kind") != claim["kind"]
                or record.get("source_ids") != json.loads(claim["source_ids_json"])
                or bool(record.get("reviewed", False)) != bool(claim["reviewed"])
                or record.get("reviewer", "") != claim["reviewer"]
                or record.get("reviewed_at", "") != claim["reviewed_at"]
            ):
                checks.append(_check("critical", "claim_ledger_mismatch", f"Claim {claim['id']} differs from its persisted record."))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        checks.append(_check("critical", "source_ledger_invalid", f"Source ledger is invalid: {exc}"))

    for claim in claims:
        refs = json.loads(claim["source_ids_json"])
        if claim["kind"] == "fact" and not refs:
            checks.append(_check("critical", "unsupported_claim", f"Factual claim {claim['id']} has no source."))
        elif any(ref not in known_source_ids for ref in refs):
            checks.append(_check("critical", "unknown_claim_source", f"Claim {claim['id']} cites an unknown source."))
        elif claim["kind"] == "uncertain" and not claim["uncertainty"]:
            checks.append(_check("medium", "uncertainty_unexplained", f"Claim {claim['id']} needs an uncertainty note."))
        if not claim["reviewed"] or not claim["reviewer"].strip() or not claim["reviewed_at"].strip():
            checks.append(_check(
                "critical", "claim_not_human_reviewed",
                f"Claim {claim['id']} has not been explicitly marked as human-reviewed.",
            ))
        script_path = package / "script.md"
        if claim["kind"] == "fact" and script_path.is_file():
            script_text = script_path.read_text(encoding="utf-8")
            narration = script_text.partition("## Narration")[2]
            if not narration or f"[{claim['id']}]" not in narration:
                checks.append(_check("critical", "claim_not_in_script", f"Factual claim {claim['id']} is not cited in the script."))
    if not claims:
        checks.append(_check("critical", "no_claim_ledger", "No source-linked, human-reviewed claims exist; factual content cannot be approved."))
    if claims and not any(check["code"] in {"unsupported_claim", "unknown_claim_source"} for check in checks):
        checks.append(_check("info", "claims_have_sources", "Every factual claim references a recorded source."))

    try:
        asset_ledger = json.loads((package / "asset_ledger.json").read_text(encoding="utf-8"))
        asset_records = {record["id"]: record for record in asset_ledger.get("assets", [])}
        if set(asset_records) != {row["id"] for row in assets}:
            checks.append(_check("critical", "asset_ledger_mismatch", "Asset ledger does not match persisted asset records."))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        asset_records = {}
        checks.append(_check("critical", "asset_ledger_invalid", f"Asset ledger is invalid: {exc}"))
    for asset in assets:
        path = Path(asset["path"])
        if (
            asset["licence"] not in ALLOWED_MEDIA_LICENSES
            or not asset["commercial_use"]
            or not asset["attribution"].strip()
            or not asset["title"].strip()
            or not asset["publisher"].strip()
            or not asset["creator"].strip()
            or not asset["retrieved_at"].strip()
        ):
            checks.append(_check("critical", "asset_rights_invalid", f"Asset {asset['id']} does not have approved rights."))
        elif not path.is_file() or sha256_file(path) != asset["file_sha256"]:
            checks.append(_check("critical", "asset_missing_or_changed", f"Asset {asset['id']} is missing or changed."))
        record = asset_records.get(asset["id"], {})
        if (
            record.get("file_sha256") != asset["file_sha256"]
            or record.get("title") != asset["title"]
            or record.get("publisher") != asset["publisher"]
            or record.get("licence") != asset["licence"]
            or record.get("licence_url") != asset["licence_url"]
            or record.get("attribution") != asset["attribution"]
            or record.get("media_type", "image") != asset["media_type"]
        ):
            checks.append(_check("critical", "asset_ledger_mismatch", f"Asset ledger entry {asset['id']} differs from its persisted record."))
    attribution_path = package / "attribution.md"
    has_map_scene = False
    map_manifest_path = package / "map_scenes.json"
    if map_manifest_path.is_file():
        try:
            map_manifest = json.loads(map_manifest_path.read_text(encoding="utf-8"))
            scene_entries = map_manifest.get("scenes") if isinstance(map_manifest, dict) else None
            if not isinstance(scene_entries, list) or not scene_entries:
                raise ValueError("Map-scene manifest must contain at least one scene.")
            for entry in scene_entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    raise ValueError("Each map scene needs a relative path.")
                scene_candidate = package / entry["path"]
                if scene_candidate.is_symlink():
                    raise ValueError("Map scene files cannot be symbolic links.")
                scene_path = scene_candidate.resolve(strict=True)
                if not scene_path.is_relative_to(package.resolve()):
                    raise ValueError("Map scene path is outside the job package.")
                scene_data = validate_map_scene(scene_path)
                has_map_scene = True
                attribution = (
                    f"Made with {scene_data['dataset_name']} "
                    f"{scene_data['dataset_version']} ({scene_data['licence']})"
                )
                if not attribution_path.is_file() or attribution not in attribution_path.read_text(
                    encoding="utf-8"
                ):
                    checks.append(_check(
                        "critical", "map_attribution_missing",
                        f"Add this dataset credit to attribution.md: {attribution}.",
                    ))
            checks.append(_check(
                "info", "map_scenes_valid",
                "Generated map scenes have verified segment hashes and Natural Earth dataset metadata.",
            ))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, MapAnimationError) as exc:
            checks.append(_check(
                "critical", "map_scene_invalid",
                f"Map scene or dataset manifest is invalid: {exc}",
            ))
    if not assets and not has_map_scene:
        checks.append(_check("critical", "no_rights_cleared_visuals", "No rights-cleared visual assets are registered."))
    elif (
        not any(asset["media_type"] in {"image", "video"} for asset in assets)
        and not has_map_scene
    ):
        checks.append(_check("critical", "no_rights_cleared_visuals", "No rights-cleared visual assets are registered."))
    if assets and not attribution_path.is_file():
        checks.append(_check("critical", "missing_attribution_report", "Asset attribution report is missing."))
    elif assets:
        attribution_text = attribution_path.read_text(encoding="utf-8")
        for asset in assets:
            if asset["attribution"] not in attribution_text:
                checks.append(_check("critical", "asset_attribution_missing", f"Attribution for asset {asset['id']} is missing."))

    required_package_files = [
        "script.md", "metadata.json", "thumbnail.jpg",
        "source_ledger.json", "asset_ledger.json",
    ]
    if not (package / "thumbnail_scores.json").is_file():
        required_package_files.append("thumbnail.svg")
    for required in required_package_files:
        if not (package / required).is_file():
            checks.append(_check("critical", "missing_package_file", f"Required package file is missing: {required}."))
    thumbnail_path = package / "thumbnail.jpg"
    if thumbnail_path.is_file():
        try:
            ffprobe = shutil.which(config.ffprobe)
            if not ffprobe:
                raise RuntimeError(f"FFprobe executable not found: {config.ffprobe}")
            result = subprocess.run(
                [
                    ffprobe, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name,width,height", "-of", "json",
                    str(thumbnail_path),
                ],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if result.returncode:
                raise RuntimeError(f"FFprobe failed: {result.stderr[-1000:]}")
            thumbnail_stream = json.loads(result.stdout)["streams"][0]
            if (
                thumbnail_stream.get("codec_name") != "mjpeg"
                or thumbnail_stream.get("width") != 1280
                or thumbnail_stream.get("height") != 720
            ):
                checks.append(_check(
                    "critical", "thumbnail_invalid",
                    "Thumbnail must be a readable 1280x720 JPEG.",
                ))
            else:
                checks.append(_check("info", "thumbnail_valid", "1280x720 JPEG thumbnail is readable."))
        except (OSError, RuntimeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            checks.append(_check("critical", "thumbnail_invalid", f"Thumbnail validation failed: {exc}"))
    thumbnail_scores_path = package / "thumbnail_scores.json"
    if thumbnail_scores_path.is_file():
        try:
            thumbnail_scores = json.loads(thumbnail_scores_path.read_text(encoding="utf-8"))
            concepts = thumbnail_scores.get("concepts")
            winner_scores = thumbnail_scores.get("winner_scores")
            if not isinstance(concepts, list) or len(concepts) < 3:
                raise ValueError("Generate at least three distinct thumbnail concepts.")
            if not isinstance(winner_scores, dict):
                raise ValueError("Record winner scores for all required dimensions.")
            if not isinstance(thumbnail_scores.get("winner"), str):
                raise ValueError("Record the selected thumbnail concept.")
            if len({
                entry.get("concept_id")
                for entry in concepts if isinstance(entry, dict)
            }) < 3:
                raise ValueError("The three thumbnail concepts must be distinct.")
            selected = next(
                (
                    entry for entry in concepts
                    if isinstance(entry, dict)
                    and entry.get("concept_id") == thumbnail_scores["winner"]
                ),
                None,
            )
            if selected is None or selected.get("scores") != winner_scores:
                raise ValueError("Selected concept and winner score record do not match.")
            for name in (
                "mobile_readability", "contrast", "text_size", "style_match",
                "geographic_accuracy", "title_relevance",
            ):
                if not isinstance(winner_scores.get(name), (int, float)):
                    raise ValueError(f"Winner score {name} is missing or invalid.")
            for filename in (
                "thumbnail_contact_sheet.jpg", "thumbnail_mobile_preview.jpg",
            ):
                if not (package / filename).is_file():
                    raise ValueError(f"Missing thumbnail review artifact: {filename}.")
            for entry in concepts:
                if not isinstance(entry, dict):
                    raise ValueError("Each thumbnail concept score must be an object.")
                for field in ("image", "editable_source"):
                    relative = entry.get(field)
                    if not isinstance(relative, str):
                        raise ValueError(f"Each concept needs a relative {field} path.")
                    artifact = (package / relative).resolve(strict=True)
                    if not artifact.is_relative_to(package.resolve()) or not artifact.is_file():
                        raise ValueError(f"Concept {field} is outside or missing from the package.")
            from PIL import Image

            expected_dimensions = {
                "thumbnail_contact_sheet.jpg": (1200, 225),
                "thumbnail_mobile_preview.jpg": (160, 90),
            }
            for filename, dimensions in expected_dimensions.items():
                with Image.open(package / filename) as preview:
                    if preview.size != dimensions:
                        raise ValueError(
                            f"{filename} must be {dimensions[0]}x{dimensions[1]}."
                        )
            if winner_scores["style_match"] < 70:
                checks.append(_check(
                    "critical", "thumbnail_style_match_low",
                    "Improve map hero, highlighted region, arrow, saturation, 2-5 word headline, "
                    "clear bottom-right badge area, and 160px legibility before approval.",
                ))
            if winner_scores["mobile_readability"] < 70:
                checks.append(_check(
                    "critical", "thumbnail_mobile_readability_low",
                    "Shorten the headline or increase its size/contrast; inspect the 160px preview.",
                ))
            for key, threshold, code, improvement in (
                (
                    "contrast", 45, "thumbnail_contrast_low",
                    "Increase the headline/background contrast and inspect the mobile preview.",
                ),
                (
                    "text_size", 60, "thumbnail_text_too_small",
                    "Increase the headline font size or reduce the headline to 2-5 short words.",
                ),
                (
                    "geographic_accuracy", 80, "thumbnail_geography_unverified",
                    "Choose a country present in the recorded dataset and verify the map crop and boundaries.",
                ),
                (
                    "title_relevance", 40, "thumbnail_title_relevance_low",
                    "Use a concise headline that clearly matches the documentary topic and title.",
                ),
            ):
                if winner_scores[key] < threshold:
                    checks.append(_check("critical", code, improvement))
            checks.append(_check(
                "info", "thumbnail_concepts_scored",
                f"{len(concepts)} concepts were scored; review the contact sheet and mobile preview. "
                "Scores are heuristic and do not predict views.",
            ))
        except (ImportError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            checks.append(_check(
                "critical", "thumbnail_scores_invalid",
                f"Thumbnail concept scoring package needs correction: {exc}",
            ))
    if (package / "metadata.json").is_file():
        try:
            metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
            if not str(metadata.get("title", "")).strip() or not str(metadata.get("description", "")).strip():
                checks.append(_check("critical", "metadata_incomplete", "Metadata title and description are required."))
        except (OSError, json.JSONDecodeError):
            checks.append(_check("critical", "metadata_invalid", "Metadata JSON is unreadable."))
    checks.append(_check("medium", "manual_review_required", "Check factual nuance, title/thumbnail accuracy, black/frozen frames, levels, and policy manually."))

    report: dict[str, Any] = {
        "job_id": job_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "critical_failures": sum(check["severity"] == "critical" for check in checks),
        "approval_blocked": any(check["severity"] == "critical" for check in checks),
        "automatic_review_limits": [
            "Automated checks cannot establish factual accuracy or detect every misleading edit.",
            "Manual full-length viewing/listening and current platform-policy review are required.",
        ],
    }
    package.mkdir(parents=True, exist_ok=True)
    (package / "qa_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    markdown = [
        f"# QA report — {job['topic']}",
        "",
        f"**Approval blocked:** {'yes' if report['approval_blocked'] else 'no'}",
        f"**Critical failures:** {report['critical_failures']}",
        "",
    ]
    markdown.extend(
        f"- **{check['severity'].upper()} — {check['code']}:** {check['message']}"
        for check in checks
    )
    markdown.append("")
    (package / "qa_report.md").write_text("\n".join(markdown), encoding="utf-8")
    return report


def assert_approvable(job: dict[str, Any], package: Path) -> dict[str, Any]:
    report_path = package / "qa_report.json"
    if not report_path.is_file():
        raise ValueError("A current QA report is required before approval.")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("job_id") != job["id"] or report.get("approval_blocked"):
        raise ValueError("QA has critical failures; approval is blocked.")
    if not (package / "final.mp4").is_file() or not (package / "metadata.json").is_file():
        raise ValueError("Final video and metadata must exist before approval.")
    return report
