#!/usr/bin/env python3
"""Record constrained production-structure notes for public YouTube videos."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

MODEL = "gemini-3.8-flash"
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent"
)
TIMEOUT_SECONDS = 180
HOOK_TYPES = [
    "question",
    "surprising_fact",
    "visual_reveal",
    "scenario",
    "other",
    "unclear",
]
CHAPTER_PATTERNS = [
    "question_context_cause_consequence_conclusion",
    "chronological",
    "thematic",
    "case_study",
    "other",
    "unclear",
]
GRAPHIC_TYPES = [
    "maps",
    "charts",
    "satellite_or_aerial_imagery",
    "archival_or_stock_footage",
    "labels_or_callouts",
    "animated_diagrams",
    "other",
]
UNCERTAINTY_TREATMENTS = [
    "explicit_verbal_qualification",
    "on_screen_qualification",
    "attribution_to_sources_or_experts",
    "contrasting_viewpoints",
    "no_clear_treatment_observed",
    "unclear",
]

PROMPT = """Analyze this video ONLY for production structure. Do not summarize its
subject matter, reproduce or refer to any spoken/on-screen wording, provide a
transcript, or include quotations. Return only the requested JSON fields:
- hook_type: choose one allowed category based on the opening's form, not its wording.
- hook_length_seconds: estimate the opening hook's duration, or null if unclear.
- chapter_pattern: choose one allowed broad structural pattern.
- map_or_graphic_screen_time_percent: estimate the share of total screen time with
  maps or explanatory graphics visible, as 0-100, or null if it cannot be estimated.
- typical_shot_length_seconds: estimate a typical shot duration, or null if unclear.
- narration_pace_wpm: estimate narration words per minute, or null if unclear.
- graphic_types: choose only applicable allowed categories; use [] if not observable.
- uncertainty_treatment: choose the best allowed category; use unclear if uncertain.
Do not infer unseen content. Estimates may be approximate; use null/unclear rather
than guessing. Follow the response schema exactly."""


def _youtube_video_id(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.fullmatch(
                r"/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})/?",
                parsed.path,
            )
            video_id = match.group(1) if match else ""
    elif host in {"youtu.be", "www.youtu.be"}:
        match = re.fullmatch(r"/([A-Za-z0-9_-]{11})/?", parsed.path)
        video_id = match.group(1) if match else ""
    else:
        return None
    return video_id if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) else None


def _validate_analysis(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Gemini did not return a JSON object.")

    required = {
        "hook_type",
        "hook_length_seconds",
        "chapter_pattern",
        "map_or_graphic_screen_time_percent",
        "typical_shot_length_seconds",
        "narration_pace_wpm",
        "graphic_types",
        "uncertainty_treatment",
    }
    if set(value) != required:
        raise ValueError("Gemini response did not match the requested structure.")
    if value["hook_type"] not in HOOK_TYPES:
        raise ValueError("Gemini returned an unsupported hook category.")
    if value["chapter_pattern"] not in CHAPTER_PATTERNS:
        raise ValueError("Gemini returned an unsupported chapter category.")
    if value["uncertainty_treatment"] not in UNCERTAINTY_TREATMENTS:
        raise ValueError("Gemini returned an unsupported uncertainty category.")
    if (
        not isinstance(value["graphic_types"], list)
        or any(item not in GRAPHIC_TYPES for item in value["graphic_types"])
        or len(set(value["graphic_types"])) != len(value["graphic_types"])
    ):
        raise ValueError("Gemini returned unsupported graphic categories.")

    for field, minimum, maximum in (
        ("hook_length_seconds", 0, 3600),
        ("map_or_graphic_screen_time_percent", 0, 100),
        ("typical_shot_length_seconds", 0, 3600),
        ("narration_pace_wpm", 0, 1000),
    ):
        item = value[field]
        if item is not None and (
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not minimum <= item <= maximum
        ):
            raise ValueError(f"Gemini returned an invalid {field} estimate.")
    return {field: value[field] for field in sorted(required)}


def _response_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gemini returned no analysis candidate.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    if not text:
        raise ValueError("Gemini returned an empty analysis.")
    return text


def _short_http_message(error: HTTPError, api_key: str) -> str:
    try:
        body = error.read(4096).decode("utf-8", errors="replace")
        parsed = json.loads(body)
        message = parsed.get("error", {}).get("message", "")
    except (OSError, json.JSONDecodeError, AttributeError):
        message = ""
    if not isinstance(message, str) or not message:
        message = "Gemini request failed."
    message = message.replace(api_key, "[REDACTED]")
    return " ".join(message.split())[:240]


def _analyze(url: str, api_key: str) -> dict[str, Any]:
    payload = {
        "contents": [{
            "parts": [
                {
                    "fileData": {
                        "mimeType": "video/mp4",
                        "fileUri": url,
                    }
                },
                {"text": PROMPT},
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "hook_type": {"type": "STRING", "enum": HOOK_TYPES},
                    "hook_length_seconds": {"type": "NUMBER", "nullable": True},
                    "chapter_pattern": {"type": "STRING", "enum": CHAPTER_PATTERNS},
                    "map_or_graphic_screen_time_percent": {
                        "type": "NUMBER",
                        "nullable": True,
                    },
                    "typical_shot_length_seconds": {
                        "type": "NUMBER",
                        "nullable": True,
                    },
                    "narration_pace_wpm": {"type": "NUMBER", "nullable": True},
                    "graphic_types": {
                        "type": "ARRAY",
                        "items": {"type": "STRING", "enum": GRAPHIC_TYPES},
                    },
                    "uncertainty_treatment": {
                        "type": "STRING",
                        "enum": UNCERTAINTY_TREATMENTS,
                    },
                },
                "required": [
                    "hook_type",
                    "hook_length_seconds",
                    "chapter_pattern",
                    "map_or_graphic_screen_time_percent",
                    "typical_shot_length_seconds",
                    "narration_pace_wpm",
                    "graphic_types",
                    "uncertainty_treatment",
                ],
            },
        },
    }
    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        result = json.loads(response.read().decode("utf-8"))
    return _validate_analysis(json.loads(_response_text(result)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record production-structure notes for 2-3 public YouTube videos."
    )
    parser.add_argument(
        "video_urls",
        nargs="+",
        metavar="YOUTUBE_URL",
        help="2-3 public YouTube video URLs",
    )
    args = parser.parse_args(argv)
    if not 2 <= len(args.video_urls) <= 3:
        parser.error("provide exactly 2 or 3 YouTube video URLs")
    if any(_youtube_video_id(url) is None for url in args.video_urls):
        parser.error("every URL must be a supported youtube.com or youtu.be video URL")

    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as error:
        print(f"Cannot read configuration: {error}", file=sys.stderr)
        return 2
    api_key = config.get("gemini_api_key") if isinstance(config, dict) else None
    if not isinstance(api_key, str) or not api_key.strip():
        print("config.json must contain a non-empty gemini_api_key.", file=sys.stderr)
        return 2
    api_key = api_key.strip()

    notes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for url in args.video_urls:
        try:
            notes.append({"video_url": url, "analysis": _analyze(url, api_key)})
        except HTTPError as error:
            message = _short_http_message(error, api_key)
            print(f"Gemini HTTP {error.code} for {url}: {message}", file=sys.stderr)
            errors.append({
                "video_url": url,
                "http_status": error.code,
                "message": message,
            })
        except (URLError, TimeoutError, OSError) as error:
            message = " ".join(str(error).replace(api_key, "[REDACTED]").split())[:240]
            print(f"Gemini request failed for {url}: {message}", file=sys.stderr)
            errors.append({"video_url": url, "message": message})
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as error:
            message = f"Gemini response was unusable: {error}"
            print(f"{url}: {message}", file=sys.stderr)
            errors.append({"video_url": url, "message": message})

    output_path = project_root / "reference" / "gemini_video_notes.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "scope": "Production structure only; no transcripts or quotations requested or stored.",
        "notes": notes,
        "errors": errors,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(notes)} video analyses and {len(errors)} errors to {output_path}.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
