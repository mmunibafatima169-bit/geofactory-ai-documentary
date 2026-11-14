"""Command-line entry point for the local documentary factory."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from geofactory.agents.research_agent import (
    discover_wikipedia_sources, export_ledger, import_ledger,
    mark_claim_reviewed,
)
from geofactory.agents.script_agent import write_script_preview
from geofactory.agents.topic_agent import propose_topics
from geofactory.analytics.feedback import import_csv, report as analytics_report
from geofactory.app.dashboard import serve
from geofactory.core.config import ConfigurationError, FactoryConfig, load_config
from geofactory.core.database import Database
from geofactory.core.jobs import (
    approval_is_current, create_job, get_job, list_jobs, package_digest,
    record_approval, transition_job,
)
from geofactory.media.asset_manager import (
    export_asset_ledger, register_asset, register_music_asset,
    search_and_download_commons, search_and_download_stock_videos,
    sha256_file, write_attribution_report,
)
from geofactory.media.map_animation_engine import (
    MapSceneSpec, create_map_scene, validate_map_scene,
)
from geofactory.media.tts_engine import (
    audio_duration_seconds, synthesize, write_text_only_narration,
)
from geofactory.studio.documentary_planner import run_documentary_plan, validate_documentary_plan
from geofactory.media.thumbnail_maker import make_thumbnail
from geofactory.media.thumbnail_engine import generate_thumbnail_concepts
from geofactory.media.video_editor import RenderError, render_video
from geofactory.media.documentary_renderer import render_documentary_from_plan, DocumentaryRenderError
from geofactory.media.shorts_generator import generate_shorts_from_documentary, ShortsRenderError
from geofactory.pipeline.orchestrator import run_pipeline_from_cli, PipelineError
from geofactory.media.remotion_renderer import render_documentary_remotion, RemotionRendererError
from geofactory.publishing.youtube_client import upload_approved_video
from geofactory.quality.qa_engine import assert_approvable, run_qa, validate_srt
from geofactory.scheduler.worker import process_offline_job, recover_and_process


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geofactory", description="Local-first geography documentary tools")
    parser.add_argument("--config", type=Path, help="JSON configuration path (defaults to ./config.json)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create local config and initialize the SQLite database")
    sub.add_parser("doctor", help="Check machine capabilities and application health")
    topics = sub.add_parser("topics", help="Generate locally scored topic proposals")
    topics.add_argument("--limit", type=int, default=5)

    new = sub.add_parser("new", help="Save a topic proposal as a persistent job")
    new.add_argument("--topic", required=True)
    new.add_argument("--question", required=True)

    demo = sub.add_parser("demo", help="Build a clearly labelled offline sample package")
    demo.add_argument("--topic", default="River cities")
    demo.add_argument("--question", default="Why do some cities grow around rivers?")

    research = sub.add_parser("research", help="Import a human-prepared source and claim ledger")
    research.add_argument("job_id")
    research.add_argument("--ledger", type=Path, required=True)

    online_research = sub.add_parser(
        "research-online", help="Search English Wikipedia and record licensed source leads"
    )
    online_research.add_argument("job_id")
    online_research.add_argument("--query", required=True)
    online_research.add_argument("--limit", type=int, default=5)

    commons = sub.add_parser(
        "commons-search", help="Find, licence-check, and download Wikimedia Commons images"
    )
    commons.add_argument("job_id")
    commons.add_argument("--query", required=True)
    commons.add_argument("--limit", type=int, default=8)
    commons.add_argument("--downloads", type=int, default=3)

    stock = sub.add_parser(
        "stock-search", help="Search/download videos through Pexels or Pixabay's official API"
    )
    stock.add_argument("job_id")
    stock.add_argument("--provider", choices=("pexels", "pixabay"), required=True)
    stock.add_argument("--query", required=True)
    stock.add_argument("--limit", type=int, default=5)
    stock.add_argument("--downloads", type=int, default=2)

    map_build = sub.add_parser(
        "map-build", help="Render a qualified Natural Earth country zoom and thumbnail concepts"
    )
    map_build.add_argument("job_id")
    map_build.add_argument("--country", required=True, help="Three-letter ISO A3 country code")
    map_build.add_argument("--duration", type=float, default=10.0)
    map_build.add_argument("--title", default="")

    thumbnail_build = sub.add_parser(
        "thumbnail-build", help="Generate, score, and compare three original map-first concepts"
    )
    thumbnail_build.add_argument("job_id")
    thumbnail_build.add_argument("--country", required=True, help="Three-letter ISO A3 country code")
    thumbnail_build.add_argument("--headline", help="Original 2-5 word headline")

    online_demo = sub.add_parser(
        "demo-online", help="Build a real Wikipedia/Commons research package; no publish/render claim"
    )
    online_demo.add_argument("--topic", default="Venice and its lagoon")
    online_demo.add_argument(
        "--question", default="How has the setting of Venice shaped its relationship with the sea?"
    )
    online_demo.add_argument("--research-query", default="Venice lagoon geography")
    online_demo.add_argument("--visual-query", default="Venice lagoon aerial")
    online_demo.add_argument("--limit", type=int, default=5)
    online_demo.add_argument("--downloads", type=int, default=2)

    script = sub.add_parser("script", help="Write an evidence-aware script preview")
    script.add_argument("job_id")

    asset = sub.add_parser("asset-add", help="Register one local asset after rights verification")
    asset.add_argument("job_id")
    asset.add_argument("--file", type=Path, required=True)
    asset.add_argument("--origin-url", required=True)
    asset.add_argument("--creator", required=True)
    asset.add_argument("--licence", required=True)
    asset.add_argument("--attribution", required=True)
    asset.add_argument("--commercial-use", action="store_true", required=True)

    music = sub.add_parser(
        "music-add", help="Register owner-downloaded music after checking its licence"
    )
    music.add_argument("job_id")
    music.add_argument("--file", type=Path, required=True)
    music.add_argument("--origin-url", required=True)
    music.add_argument("--creator", required=True)
    music.add_argument("--license", required=True)
    music.add_argument("--attribution", required=True)
    music.add_argument("--commercial-use", action="store_true", required=True)

    narrate = sub.add_parser("narrate", help="Generate local narration or labelled text-only script")
    narrate.add_argument("job_id")
    narrate.add_argument("--text-file", type=Path, required=True)

    render = sub.add_parser("render", help="Render from registered assets and narration using FFmpeg")
    render.add_argument("job_id")

    plan = sub.add_parser(
        "plan", help="Visual Director: build scene_manifest.json from the narration plan"
    )
    plan.add_argument("job_id")
    plan.add_argument("--title", default="Documentary draft")

    doc_plan = sub.add_parser(
        "plan-documentary", help="Build full 8-15 min documentary plan with chapters, scenes, and asset allocations"
    )
    doc_plan.add_argument("job_id")
    doc_plan.add_argument("--duration", type=float, default=600.0, help="Target duration in seconds (480-900)")
    doc_plan.add_argument("--title", default="Documentary draft")
    doc_render = sub.add_parser(
        "render-documentary", help="Render full documentary from documentary plan (scene_manifest.json + asset_allocations.json)"
    )
    doc_render.add_argument("job_id")
    doc_render.add_argument("--output", default="final.mp4", help="Output filename in package directory")

    remotion_render = sub.add_parser(
        "remotion-render", help="Render full documentary via Remotion motion graphics engine (1080p)"
    )
    remotion_render.add_argument("job_id")
    remotion_render.add_argument("--output", default="remotion_final.mp4", help="Output filename in package directory")
    remotion_render.add_argument("--composition", default="DynamicDocumentary", help="Remotion composition ID")

    shorts = sub.add_parser(
        "shorts", help="Generate YouTube Shorts (15-60s vertical) from documentary assets"
    )
    shorts.add_argument("job_id")
    shorts.add_argument("--duration", type=float, default=45.0, help="Target duration in seconds (15-60)")
    shorts.add_argument("--output", default="shorts.mp4", help="Output filename in package directory")
    shorts.add_argument("--hook", help="Custom hook text for opening (auto-generated from script if omitted)")
    produce = sub.add_parser(
        "produce", help="Run complete end-to-end documentary production pipeline (research → script → plan → narrate → render → shorts → qa)"
    )
    produce.add_argument("job_id")
    produce.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    produce.add_argument("--duration", type=float, default=600.0, help="Documentary target duration in seconds (480-900)")
    produce.add_argument("--shorts-duration", type=float, default=45.0, help="Shorts target duration in seconds (15-60)")
    produce.add_argument("--hook", help="Custom hook text for Shorts opening")
    produce.add_argument("--research-query", help="Research query (defaults to job topic)")
    produce.add_argument("--research-limit", type=int, default=10, help="Max Wikipedia sources to fetch")




    editorial = sub.add_parser(
        "editorial-report", help="Editorial QC: reuse/static checks + contact sheet"
    )
    editorial.add_argument("job_id")

    qa = sub.add_parser("qa", help="Run release-gate checks for a job")
    qa.add_argument("job_id")

    approve = sub.add_parser("approve", help="Approve exact final package bytes after passing QA")
    approve.add_argument("job_id")
    approve.add_argument("--reviewer", default="local owner")
    approve.add_argument("--note", default="")

    claim_review = sub.add_parser(
        "claims-review",
        help="Inspect claims or mark one claim as verified against its cited sources",
    )
    claim_review.add_argument("job_id")
    claim_review.add_argument("--claim-id", help="Claim to attest after checking its cited evidence")
    claim_review.add_argument("--reviewer", help="Name of the person who performed the review")
    claim_review.add_argument(
        "--confirm-reviewed", action="store_true",
        help="Confirm this specific claim was checked against its cited evidence",
    )

    reject = sub.add_parser("reject", help="Reject a job")
    reject.add_argument("job_id")
    reject.add_argument("--note", default="Rejected by owner.")

    sub.add_parser("status", help="List persisted jobs")
    work = sub.add_parser("work", help="Recover interrupted jobs and process queued proposals")
    work.add_argument("--max-jobs", type=int, default=1)
    review_ready = sub.add_parser("review-ready", help="Mark a manually revised package ready for review")
    review_ready.add_argument("job_id")
    dashboard = sub.add_parser("serve", help="Start the loopback-only approval dashboard")
    dashboard.add_argument("--port", type=int, help="Override the configured local port")

    backup = sub.add_parser("backup", help="Create a consistent SQLite backup")
    backup.add_argument("--destination", type=Path, required=True)

    analytics = sub.add_parser("analytics-import", help="Import owner-provided analytics CSV")
    analytics.add_argument("csv_file", type=Path)
    sub.add_parser("analytics-report", help="Summarize imported analytics descriptively")

    upload = sub.add_parser("upload", help="Attempt the fail-closed optional upload path")
    upload.add_argument("job_id")
    return parser


def _init(config_path: Path | None, config: FactoryConfig) -> None:
    effective_path = config_path or (Path.cwd() / "config.json")
    if not effective_path.exists():
        effective_path.parent.mkdir(parents=True, exist_ok=True)
        effective_path.write_text(
            json.dumps(_example_config(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"Created {effective_path}")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    Database(config.database_path).initialize()
    print(f"Database ready: {config.database_path}")


def _example_config() -> dict[str, Any]:
    return {
        "root": ".",
        "database_path": "data/geofactory.sqlite3",
        "output_dir": "output",
        "channel_name": "CHANNEL_NAME_TBD",
        "bind_host": "127.0.0.1",
        "dashboard_port": 8765,
        "require_topic_approval": True,
        "dry_run": True,
        "publishing_enabled": False,
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
        "tts_backend": "edge-tts",
        "edge_tts_voice": "en-US-GuyNeural",
        "groq_api_key": "",
        "groq_model": "llama-3.3-70b-versatile",
        "pexels_api_key": "",
        "pixabay_api_key": "",
        "piper_executable": "piper",
        "piper_voice_model": "",
        "piper_voice_license": "",
        "espeak_executable": "espeak-ng",
        "espeak_voice": "en-us",
        "espeak_speed": 155,
        "local_llm_url": "http://127.0.0.1:11434",
        "local_llm_model": "",
        "minimum_free_disk_gb": 2.0,
        "width": 1920,
        "height": 1080,
    }


def _doctor(config: FactoryConfig) -> dict[str, Any]:
    usage = shutil.disk_usage(config.root)
    tools = {}
    for name, executable in (
        ("ffmpeg", config.ffmpeg),
        ("ffprobe", config.ffprobe),
        ("ollama", "ollama"),
        ("piper", config.piper_executable),
        ("espeak-ng", config.espeak_executable),
        ("edge-tts", "edge-tts"),
    ):
        tools[name] = shutil.which(executable) or "not found"
    memory: dict[str, str] = {}
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith(("MemTotal:", "MemAvailable:")):
                memory[line.split(":", 1)[0]] = line.split(":", 1)[1].strip()
    gpu = shutil.which("nvidia-smi")
    gpu_info = "nvidia-smi not found"
    if gpu:
        result = subprocess.run([gpu, "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
        gpu_info = result.stdout.strip() if result.returncode == 0 else "GPU query failed"
    db = Database(config.database_path)
    db.initialize()
    required_tools = ["ffmpeg", "ffprobe"]
    if config.tts_backend == "espeak-ng":
        required_tools.append("espeak-ng")
    elif config.tts_backend == "piper":
        required_tools.append("piper")
    elif config.tts_backend == "edge-tts":
        required_tools.append("edge-tts")
    missing_tools = [name for name in required_tools if tools[name] == "not found"]
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "machine": __import__("platform").machine(),
        "memory": memory,
        "disk_free_bytes": usage.free,
        "disk_free_gib": round(usage.free / (1024 ** 3), 2),
        "gpu": gpu_info,
        "tools": tools,
        "tts_backend": config.tts_backend,
        "database": str(config.database_path),
        "dashboard_bind": f"{config.bind_host}:{config.dashboard_port}",
        "publishing_enabled": config.publishing_enabled,
        "assessment": (
            f"Missing configured media executables: {', '.join(missing_tools)}."
            if missing_tools else
            f"Configured media executables are available; TTS backend is {config.tts_backend}."
        ),
    }


def _create_or_get_job(db: Database, config: FactoryConfig, topic: str, question: str) -> dict[str, Any]:
    return create_job(db, topic, question, config.output_dir)


def _process_demo(db: Database, config: FactoryConfig, topic: str, question: str) -> None:
    job = _create_or_get_job(db, config, topic, question)
    print(f"Job {job['id']} ({job['status']})")
    if job["status"] == "proposed":
        report = process_offline_job(db, config, job["id"])
        print(f"Offline package: {job['output_dir']}")
        print(f"Status: {get_job(db, job['id'])['status']}; critical QA failures: {report['critical_failures']}")
    else:
        print(f"Existing job package: {job['output_dir']}")


def _approve(db: Database, job_id: str, reviewer: str, note: str) -> None:
    job = get_job(db, job_id)
    if job["status"] != "awaiting_approval":
        raise ValueError(f"Job status must be awaiting_approval, not {job['status']}.")
    package = Path(job["output_dir"])
    assert_approvable(job, package)
    digest = package_digest(package)
    approval_id = record_approval(db, job_id, reviewer, note, digest)
    (package / "approval.json").write_text(
        json.dumps(
            {"approval_id": approval_id, "reviewer": reviewer, "note": note,
             "package_sha256": digest, "decision": "approved"},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Approved exact package sha256={digest}")


def _invalidate_if_package_changed(db: Database, job_id: str, package: Path) -> None:
    if get_job(db, job_id)["status"] == "approved":
        approval_is_current(db, job_id, package)


def _validate_narration_package(package: Path, config: FactoryConfig) -> None:
    manifest_path = package / "narration_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Narration manifest is missing or invalid: {exc}") from exc
    expected_hashes = {
        "audio_sha256": package / "narration.wav",
        "narration_text_sha256": package / "narration.txt",
        "subtitles_sha256": package / "subtitles.srt",
    }
    if manifest.get("mode") != "audio":
        raise ValueError("Rendering requires generated audio; text-only narration cannot be rendered.")
    for field, path in expected_hashes.items():
        if not path.is_file() or manifest.get(field) != sha256_file(path):
            raise ValueError(f"Narration package is stale or incomplete: {path.name}.")
    subtitle_problems = validate_srt(package / "subtitles.srt")
    if subtitle_problems:
        raise ValueError("Invalid subtitles: " + "; ".join(subtitle_problems))
    duration = audio_duration_seconds(package / "narration.wav", config.ffprobe)
    if abs(duration - float(manifest.get("duration_seconds", 0))) > 0.25:
        raise ValueError("Narration duration no longer matches its generation manifest.")


def _package_map_scenes(package: Path) -> list[Path]:
    manifest_path = package / "map_scenes.json"
    if not manifest_path.is_file():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Map-scene manifest is unreadable: {exc}") from exc
    entries = manifest.get("scenes") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        raise ValueError("Map-scene manifest must contain a scenes list.")
    scenes: list[Path] = []
    package_root = package.resolve()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("Map-scene entries need a relative path.")
        candidate = package / entry["path"]
        if candidate.is_symlink():
            raise ValueError("Map-scene files cannot be symbolic links.")
        path = candidate.resolve(strict=True)
        if not path.is_relative_to(package_root):
            raise ValueError("Map-scene paths must remain inside the job package.")
        validate_map_scene(path)
        scenes.append(path)
    return scenes


def run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    db = Database(config.database_path)
    db.initialize()

    if args.command == "init":
        _init(args.config, config)
    elif args.command == "doctor":
        print(json.dumps(_doctor(config), indent=2))
    elif args.command == "topics":
        if args.limit < 1 or args.limit > 25:
            raise ValueError("Topic limit must be between 1 and 25.")
        print(json.dumps(propose_topics(db, args.limit), indent=2, ensure_ascii=False))
    elif args.command == "new":
        job = _create_or_get_job(db, config, args.topic, args.question)
        print(json.dumps({"id": job["id"], "status": job["status"], "output_dir": job["output_dir"]}, indent=2))
    elif args.command == "demo":
        _process_demo(db, config, args.topic, args.question)
    elif args.command == "research":
        job = get_job(db, args.job_id)
        counts = import_ledger(db, args.job_id, args.ledger)
        export_ledger(db, args.job_id, Path(job["output_dir"]) / "source_ledger.json")
        print(json.dumps(counts, indent=2))
    elif args.command == "research-online":
        job = get_job(db, args.job_id)
        sources = discover_wikipedia_sources(
            db, args.job_id, args.query, limit=args.limit
        )
        package = Path(job["output_dir"])
        export_ledger(db, args.job_id, package / "source_ledger.json")
        write_script_preview(db, args.job_id, package / "script.md")
        print(
            json.dumps(
                {
                    "sources_added": len(sources),
                    "sources": [
                        {
                            "id": source["id"],
                            "title": source["title"],
                            "url": source["url"],
                            "publisher": source["publisher"],
                            "accessed_at": source["accessed_at"],
                            "licence": source["licence"],
                            "licence_url": source["licence_url"],
                        }
                        for source in sources
                    ],
                    "notice": "Research leads only. Verify against cited and independent sources.",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    elif args.command == "commons-search":
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        result = search_and_download_commons(
            db, args.job_id, args.query, package / "assets",
            limit=args.limit, max_downloads=args.downloads,
        )
        assets = export_asset_ledger(db, args.job_id, package / "asset_ledger.json")
        write_attribution_report(assets, package / "attribution.md")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "stock-search":
        if not 1 <= args.limit <= 10 or not 1 <= args.downloads <= 5:
            raise ValueError("Stock search limits must be 1-10 results and 1-5 downloads.")
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        result = search_and_download_stock_videos(
            db, args.job_id, args.query, package / "assets", config,
            provider=args.provider, limit=args.limit, max_downloads=args.downloads,
        )
        assets = export_asset_ledger(db, args.job_id, package / "asset_ledger.json")
        write_attribution_report(assets, package / "attribution.md")
        print(json.dumps({
            "provider": args.provider,
            "downloaded": len(result["assets"]),
            "rejected": result["rejected"],
            "notice": "Provider stock media remains subject to each platform's current licence terms and human review.",
        }, indent=2, ensure_ascii=False))
    elif args.command == "map-build":
        if not re.fullmatch(r"[A-Za-z]{3}", args.country):
            raise ValueError("Country must be a three-letter ISO A3 code.")
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        package.mkdir(parents=True, exist_ok=True)
        existing_scenes = _package_map_scenes(package)
        scene_path = package / "maps" / f"{args.country.upper()}-{len(existing_scenes) + 1:02d}.mp4"
        scene_manifest = create_map_scene(
            config.root,
            scene_path,
            MapSceneSpec(
                country_iso_a3=args.country,
                duration_seconds=args.duration,
                title=args.title,
            ),
            ffmpeg_name=config.ffmpeg,
            width=min(1280, config.width),
            height=min(720, config.height),
        )
        entries = []
        manifest_path = package / "map_scenes.json"
        if manifest_path.is_file():
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = saved.get("scenes", []) if isinstance(saved, dict) else []
            if not isinstance(entries, list):
                raise ValueError("Existing map-scene manifest has an invalid scenes list.")
        entries.append({
            "path": str(scene_path.relative_to(package)),
            "dataset_name": scene_manifest["dataset_name"],
            "dataset_version": scene_manifest["dataset_version"],
            "licence": scene_manifest["licence"],
            "dataset_download_date": scene_manifest["dataset_download_date"],
        })
        manifest_path.write_text(
            json.dumps({"scenes": entries}, indent=2) + "\n", encoding="utf-8"
        )
        attribution = package / "attribution.md"
        current = attribution.read_text(encoding="utf-8") if attribution.is_file() else ""
        map_credit = (
            f"Made with {scene_manifest['dataset_name']} "
            f"{scene_manifest['dataset_version']} ({scene_manifest['licence']}); "
            f"downloaded {scene_manifest['dataset_download_date']}. "
            f"{scene_manifest['licence_url']}"
        )
        if map_credit not in current:
            attribution.write_text(
                current.rstrip() + "\n\n## Map data\n\n" + map_credit + "\n",
                encoding="utf-8",
            )
        thumbnail_result = generate_thumbnail_concepts(
            job["topic"], args.country, package, config.root
        )
        print(json.dumps({
            "scene": str(scene_path),
            "country": scene_manifest["country_name"],
            "dataset": {
                "name": scene_manifest["dataset_name"],
                "version": scene_manifest["dataset_version"],
                "licence": scene_manifest["licence"],
                "download_date": scene_manifest["dataset_download_date"],
            },
            "thumbnail_winner": thumbnail_result["winner"],
            "thumbnail_scores": thumbnail_result["winner_scores"],
        }, indent=2, ensure_ascii=False))
    elif args.command == "thumbnail-build":
        job = get_job(db, args.job_id)
        result = generate_thumbnail_concepts(
            job["topic"], args.country, Path(job["output_dir"]), config.root,
            headline=args.headline,
        )
        print(json.dumps({
            "winner": result["winner"],
            "winner_scores": result["winner_scores"],
            "outputs": result["outputs"],
        }, indent=2, ensure_ascii=False))
    elif args.command == "demo-online":
        if not 1 <= args.limit <= 10 or not 1 <= args.downloads <= 5:
            raise ValueError("Online demo limits must be 1-10 sources and 1-5 asset downloads.")
        job = _create_or_get_job(db, config, args.topic, args.question)
        if job["status"] == "proposed":
            process_offline_job(db, config, job["id"])
        job = get_job(db, job["id"])
        package = Path(job["output_dir"])
        sources = discover_wikipedia_sources(
            db, job["id"], args.research_query, limit=args.limit
        )
        export_ledger(db, job["id"], package / "source_ledger.json")
        write_script_preview(db, job["id"], package / "script.md")
        asset_result = search_and_download_commons(
            db, job["id"], args.visual_query, package / "assets",
            limit=max(args.limit, args.downloads), max_downloads=args.downloads,
        )
        assets = export_asset_ledger(db, job["id"], package / "asset_ledger.json")
        write_attribution_report(assets, package / "attribution.md")
        if assets:
            short_title = " ".join(job["topic"].split())[:48].strip()
            make_thumbnail(
                job["topic"], short_title, package / "thumbnail.jpg", config,
                background=Path(str(assets[0]["path"])),
            )
        qa_report = run_qa(db, job["id"], config)
        print(
            json.dumps(
                {
                    "job_id": job["id"],
                    "package_dir": str(package),
                    "sources_added": len(sources),
                    "assets_downloaded_or_reused": len(asset_result["assets"]),
                    "assets_rejected": asset_result["rejected"],
                    "qa_blocked": qa_report["approval_blocked"],
                    "critical_failures": qa_report["critical_failures"],
                    "status": get_job(db, job["id"])["status"],
                    "notice": (
                        "Real source and asset discovery completed. This is not a finished video: "
                        "narration and final render still require production and human review."
                    ),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    elif args.command == "script":
        job = get_job(db, args.job_id)
        if config.groq_api_key.strip() or config.local_llm_model.strip():
            from geofactory.agents.script_agent import generate_evidence_script

            words = generate_evidence_script(
                db, args.job_id, Path(job["output_dir"]) / "script.md", config
            )
            provider = "Groq" if config.groq_api_key.strip() else "local model"
            print(f"Wrote {provider} draft with {words} words; fact-check before use.")
        else:
            words = write_script_preview(db, args.job_id, Path(job["output_dir"]) / "script.md")
            print(
                f"Wrote evidence-aware draft with {words} words; configure Groq or Ollama "
                "for a full draft."
            )
    elif args.command == "asset-add":
        job = get_job(db, args.job_id)
        asset_id = register_asset(
            db, args.job_id, args.file, args.origin_url, args.creator, args.licence,
            args.attribution, args.commercial_use,
        )
        package = Path(job["output_dir"])
        records = export_asset_ledger(db, args.job_id, package / "asset_ledger.json")
        write_attribution_report(records, package / "attribution.md")
        print(f"Registered asset {asset_id}")
    elif args.command == "music-add":
        job = get_job(db, args.job_id)
        asset_id = register_music_asset(
            db, args.job_id, args.file, args.origin_url, args.creator, args.license,
            args.attribution, args.commercial_use,
        )
        package = Path(job["output_dir"])
        records = export_asset_ledger(db, args.job_id, package / "asset_ledger.json")
        write_attribution_report(records, package / "attribution.md")
        print(f"Registered background music asset {asset_id}; render will mix it at -20 dB.")
    elif args.command == "narrate":
        job = get_job(db, args.job_id)
        text = args.text_file.read_text(encoding="utf-8")
        package = Path(job["output_dir"])
        if config.tts_backend == "none":
            write_text_only_narration(text, package / "narration.txt")
            manifest = {
                "mode": "text-only",
                "backend": "none",
                "narration_text_sha256": sha256_file(package / "narration.txt"),
                "audio_sha256": "",
                "subtitles_sha256": "",
            }
            print(
                "Saved clearly labelled text-only narration. No audio or synchronized SRT "
                "was generated; QA will block rendering."
            )
        else:
            duration = synthesize(
                text, package / "narration.wav", config,
                subtitle_destination=package / "subtitles.srt",
            )
            (package / "narration.txt").write_text(text.strip() + "\n", encoding="utf-8")
            manifest = {
                "mode": "audio",
                "backend": config.tts_backend,
                "narration_text_sha256": sha256_file(package / "narration.txt"),
                "audio_sha256": sha256_file(package / "narration.wav"),
                "subtitles_sha256": sha256_file(package / "subtitles.srt"),
                "duration_seconds": duration,
            }
            print(
                f"Generated and verified narration ({duration:.1f}s) with "
                f"sentence-timed subtitles."
            )
        manifest_path = package / "narration_manifest.json"
        temporary_manifest = manifest_path.with_suffix(".json.tmp")
        temporary_manifest.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        temporary_manifest.replace(manifest_path)
        _invalidate_if_package_changed(db, args.job_id, package)
    elif args.command == "render":
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        if job["status"] not in {"awaiting_review", "qa_failed"}:
            raise ValueError(f"Render requires awaiting_review or qa_failed, got {job['status']}.")
        _validate_narration_package(package, config)
        transition_job(db, args.job_id, "rendering", "Owner requested local FFmpeg render.")
        with db.connect() as conn:
            records = [dict(row) for row in conn.execute(
                "SELECT * FROM assets WHERE job_id = ? ORDER BY retrieved_at, id", (args.job_id,)
            )]
        images = [Path(record["path"]) for record in records]
        map_scenes = _package_map_scenes(package)
        try:
            render_video(
                config, images, package / "narration.wav", package / "final.mp4",
                records, package / "subtitles.srt", scene_videos=map_scenes,
            )
            hero_visual = next(
                (
                    Path(record["path"])
                    for record in records
                    if record.get("media_type", "image") in {"image", "video"}
                ),
                None,
            )
            if map_scenes and not (package / "thumbnail_scores.json").is_file():
                map_manifest = validate_map_scene(map_scenes[0])
                generate_thumbnail_concepts(
                    job["topic"], map_manifest["scene"]["country_iso_a3"],
                    package, config.root,
                )
            elif hero_visual is not None and not (
                package / "thumbnail_scores.json"
            ).is_file():
                make_thumbnail(
                    job["topic"],
                    " ".join(job["topic"].split())[:48].strip(),
                    package / "thumbnail.jpg",
                    config,
                    background=hero_visual,
                )
        except (RenderError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            transition_job(
                db, args.job_id, "qa_failed", "Render or thumbnail generation did not complete.",
                error=str(exc)
            )
            raise
        report = run_qa(db, args.job_id, config)
        target = "qa_failed" if report["approval_blocked"] else "awaiting_approval"
        transition_job(db, args.job_id, target, "QA completed after render.")
        print(f"Render complete. Status: {target}; critical failures: {report['critical_failures']}")
    elif args.command == "plan":
        from geofactory.studio.visual_director import (
            plan_scenes, segments_from_narration,
        )
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        script_path = package / "script.md"
        narration_path = package / "narration.txt"
        if script_path.is_file():
            raw = script_path.read_text(encoding="utf-8")
            text = raw.partition("## Narration")[2] or raw
        elif narration_path.is_file():
            text = narration_path.read_text(encoding="utf-8")
        else:
            raise SystemExit("plan requires script.md or narration.txt in the package")
        duration = 0.0
        wav = package / "narration.wav"
        if wav.is_file():
            duration = audio_duration_seconds(wav, config.ffprobe)
        if duration <= 0:
            words = len(text.split())
            duration = max(60.0, words / 2.7)
        engines = {"ffmpeg"}
        repo_root = Path(__file__).resolve().parents[2]
        if (repo_root / "studio" / "remotion" / "package.json").is_file():
            engines.add("remotion")
        if shutil.which("blender"):
            engines.add("blender")
        if shutil.which("manim"):
            engines.add("manim")
        segments = segments_from_narration(text, duration)
        manifest = plan_scenes(
            args.job_id, args.title, segments,
            engines_available=engines, width=config.width, height=config.height,
        )
        out = package / "scene_manifest.json"
        manifest.save(out)
        engines_used = sorted({s.engine for s in manifest.scenes})
        print(f"Scene manifest: {out}")
        print(f"{len(manifest.scenes)} scenes over {duration:.1f}s · engines: {', '.join(engines_used)}")
    elif args.command == "plan-documentary":
        if not 480 <= args.duration <= 900:
            raise SystemExit("Duration must be between 480 and 900 seconds (8-15 minutes)")
        plan = run_documentary_plan(db, args.job_id, config, args.duration)
        errors = validate_documentary_plan(plan)
        if errors:
            print("Validation warnings:")
            for err in errors:
                print(f"  - {err}")
        print(f"Documentary plan complete. See {Path(get_job(db, args.job_id)['output_dir'])}")
    elif args.command == "render-documentary":
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        
        # Check that documentary plan exists
        plan_path = package / "documentary_plan.json"
        manifest_path = package / "scene_manifest.json"
        allocations_path = package / "asset_allocations.json"
        
        for p in [plan_path, manifest_path, allocations_path]:
            if not p.is_file():
                raise SystemExit(f"Documentary plan not complete. Missing: {p.name}. Run 'plan-documentary' first.")
        
        # Check narration and subtitles
        narration_path = package / "narration.wav"
        subtitles_path = package / "subtitles.srt"
        if not narration_path.is_file():
            raise SystemExit(f"Narration not found: {narration_path}. Run 'narrate' first.")
        if not subtitles_path.is_file():
            raise SystemExit(f"Subtitles not found: {subtitles_path}. Run 'narrate' first.")
        
        # Check job status
        if job["status"] not in {"awaiting_review", "qa_failed"}:
            raise ValueError(f"Render requires awaiting_review or qa_failed, got {job['status']}.")
        
        transition_job(db, args.job_id, "rendering", "Owner requested documentary render from plan.")
        
        try:
            output_path = package / args.output
            render_documentary_from_plan(config, args.job_id, package, output_path)
            
            # Generate thumbnail if needed
            hero_visual = None
            from geofactory.core.database import Database
            with Database(config.database_path).connect() as conn:
                records = [dict(row) for row in conn.execute(
                    "SELECT * FROM assets WHERE job_id = ? ORDER BY retrieved_at, id", (args.job_id,)
                )]
            for record in records:
                if record.get("media_type", "image") in {"image", "video"}:
                    hero_visual = Path(record["path"])
                    break
            
            if not (package / "thumbnail_scores.json").is_file() and hero_visual is not None:
                make_thumbnail(
                    job["topic"],
                    " ".join(job["topic"].split())[:48].strip(),
                    package / "thumbnail.jpg",
                    config,
                    background=hero_visual,
                )
        except (DocumentaryRenderError, RenderError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            transition_job(
                db, args.job_id, "qa_failed", "Documentary render did not complete.",
                error=str(exc)
            )
            raise
        
        report = run_qa(db, args.job_id, config)
        target = "qa_failed" if report["approval_blocked"] else "awaiting_approval"
        transition_job(db, args.job_id, target, "QA completed after documentary render.")
        print(f"Documentary render complete. Status: {target}; critical failures: {report['critical_failures']}")
    elif args.command == "remotion-render":
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        
        # Check that documentary plan exists
        plan_path = package / "documentary_plan.json"
        manifest_path = package / "scene_manifest.json"
        allocations_path = package / "asset_allocations.json"
        
        for p in [plan_path, manifest_path, allocations_path]:
            if not p.is_file():
                raise SystemExit(f"Documentary plan not complete. Missing: {p.name}. Run 'plan-documentary' first.")
        
        # Check narration and subtitles
        narration_path = package / "narration.wav"
        subtitles_path = package / "subtitles.srt"
        if not narration_path.is_file():
            raise SystemExit(f"Narration not found: {narration_path}. Run 'narrate' first.")
        if not subtitles_path.is_file():
            raise SystemExit(f"Subtitles not found: {subtitles_path}. Run 'narrate' first.")
        
        # Check job status
        if job["status"] not in {"awaiting_review", "qa_failed"}:
            raise ValueError(f"Remotion render requires awaiting_review or qa_failed, got {job['status']}.")
        
        transition_job(db, args.job_id, "rendering", "Owner requested Remotion documentary render from plan.")
        
        try:
            output_path = package / args.output
            render_documentary_remotion(config, args.job_id, package, output_path)
        except (RemotionRendererError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            transition_job(
                db, args.job_id, "qa_failed", "Remotion documentary render did not complete.",
                error=str(exc)
            )
            raise
        
        report = run_qa(db, args.job_id, config)
        target = "qa_failed" if report["approval_blocked"] else "awaiting_approval"
        transition_job(db, args.job_id, target, "QA completed after Remotion documentary render.")
        print(f"Remotion documentary render complete. Status: {target}; critical failures: {report['critical_failures']}")
    elif args.command == "shorts":
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        
        # Check that documentary plan exists
        plan_path = package / "documentary_plan.json"
        manifest_path = package / "scene_manifest.json"
        allocations_path = package / "asset_allocations.json"
        
        for p in [plan_path, manifest_path, allocations_path]:
            if not p.is_file():
                raise SystemExit(f"Documentary plan not complete. Missing: {p.name}. Run 'plan-documentary' first.")
        
        # Check narration and subtitles
        narration_path = package / "narration.wav"
        subtitles_path = package / "subtitles.srt"
        if not narration_path.is_file():
            raise SystemExit(f"Narration not found: {narration_path}. Run 'narrate' first.")
        if not subtitles_path.is_file():
            raise SystemExit(f"Subtitles not found: {subtitles_path}. Run 'narrate' first.")
        
        # Check job status
        if job["status"] not in {"awaiting_review", "qa_failed", "awaiting_approval", "approved"}:
            raise ValueError(f"Shorts generation requires completed documentary, got {job['status']}.")
        
        try:
            output_path = package / args.output
            generate_shorts_from_documentary(
                config, args.job_id, package, output_path,
                target_duration=args.duration,
                hook_text=args.hook,
            )
        except (ShortsRenderError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            print(f"Shorts generation failed: {exc}")
            raise
        
        print(f"Shorts generated: {output_path} ({args.duration}s)")
    elif args.command == "produce":
        job = get_job(db, args.job_id)
        
        # Validate job exists
        if not job:
            raise SystemExit(f"Job not found: {args.job_id}")
        
        # Check for required API keys if not resuming
        if not args.resume:
            if not config.groq_api_key.strip() and not config.local_llm_model.strip():
                print("Warning: No Groq API key or local LLM configured. Script will use evidence-aware draft.")
            if config.tts_backend == "none":
                print("Warning: TTS backend is 'none'. Narration will be text-only; QA will block render.")
        
        try:
            run_pipeline_from_cli(
                config, args.job_id,
                resume=args.resume,
                duration=args.duration,
                shorts_duration=args.shorts_duration,
                shorts_hook=args.hook,
                research_query=args.research_query,
                research_limit=args.research_limit,
            )
        except PipelineError as e:
            print(f"Pipeline failed at {e.stage.value}: {e}")
            raise SystemExit(1)
        except Exception as e:
            print(f"Pipeline error: {e}")
            raise SystemExit(1)
        
        print(f"Pipeline completed successfully for job {args.job_id}")



    elif args.command == "editorial-report":
        from geofactory.studio.editorial_qa import build_report
        from geofactory.studio.scene_manifest import SceneManifest
        job = get_job(db, args.job_id)
        package = Path(job["output_dir"])
        manifest = SceneManifest.load(package / "scene_manifest.json")
        video = package / "final.mp4"
        report = build_report(
            manifest,
            video=video if video.is_file() else None,
            work_dir=package,
            ffmpeg=config.ffmpeg,
        )
        out = package / "editorial_report.json"
        report.save(out)
        print(f"Editorial report: {out}")
        print(
            f"scenes={report.scene_count} critical={report.critical_count} "
            f"static_max={report.static_wall_max_s:.1f}s repeats={len(report.repeated_assets)}"
        )
    elif args.command == "qa":
        job = get_job(db, args.job_id)
        had_approval = job["status"] == "approved"
        if had_approval:
            approval_is_current(db, args.job_id, Path(job["output_dir"]))
            job = get_job(db, args.job_id)
        report = run_qa(db, args.job_id, config)
        if had_approval and get_job(db, args.job_id)["status"] == "approved":
            approval_is_current(db, args.job_id, Path(job["output_dir"]))
            job = get_job(db, args.job_id)
        if job["status"] in {"qa_failed", "awaiting_approval"}:
            target = "qa_failed" if report["approval_blocked"] else "awaiting_approval"
            if target != job["status"]:
                transition_job(db, args.job_id, target, "QA state updated.")
        print(json.dumps(report, indent=2))
        if report["approval_blocked"]:
            return 1
    elif args.command == "approve":
        run_qa(db, args.job_id, config)
        _approve(db, args.job_id, args.reviewer, args.note)
    elif args.command == "claims-review":
        job = get_job(db, args.job_id)
        with db.connect() as conn:
            claims = [
                dict(row) for row in conn.execute(
                    """SELECT id, text, kind, source_ids_json, reviewed, reviewer, reviewed_at
                       FROM claims WHERE job_id=? ORDER BY id""",
                    (args.job_id,),
                )
            ]
            sources_by_id = {
                row["id"]: dict(row) for row in conn.execute(
                    """SELECT id, title, url, publisher, accessed_at, licence, evidence
                       FROM sources WHERE job_id=?""",
                    (args.job_id,),
                )
            }
            for claim in claims:
                source_ids = json.loads(claim["source_ids_json"])
                claim["sources"] = [
                    sources_by_id[source_id]
                    for source_id in source_ids
                    if source_id in sources_by_id
                ]
        if not claims:
            raise ValueError("There are no claims to review.")
        if args.claim_id is None:
            print(json.dumps({"claims": claims}, indent=2, ensure_ascii=False))
            return 0
        if not args.reviewer or not args.confirm_reviewed:
            raise ValueError(
                "Review one claim by providing --reviewer and --confirm-reviewed after inspecting its evidence."
            )
        mark_claim_reviewed(db, args.job_id, args.claim_id, args.reviewer)
        export_ledger(
            db, args.job_id, Path(job["output_dir"]) / "source_ledger.json"
        )
        _invalidate_if_package_changed(db, args.job_id, Path(job["output_dir"]))
        print(
            json.dumps(
                {
                    "claim_marked_reviewed": args.claim_id,
                    "reviewer": args.reviewer,
                    "confirmation": "Owner attests this claim was checked against its cited sources.",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    elif args.command == "reject":
        transition_job(db, args.job_id, "rejected", args.note)
        print("Job rejected.")
    elif args.command == "status":
        rows = list_jobs(db)
        for row in rows:
            if row["status"] == "approved":
                approval_is_current(db, row["id"], Path(row["output_dir"]))
        print(json.dumps(list_jobs(db), indent=2))
    elif args.command == "work":
        processed = recover_and_process(db, config, args.max_jobs)
        print(json.dumps({"processed_job_ids": processed}, indent=2))
    elif args.command == "review-ready":
        transition_job(
            db, args.job_id, "awaiting_review",
            "Owner marked revised package ready for review; rerun QA before approval.",
        )
        print("Package marked awaiting_review. Run QA and review all files.")
    elif args.command == "serve":
        if args.port is not None:
            if not 1024 <= args.port <= 65535:
                raise ValueError("Dashboard port must be between 1024 and 65535.")
            from dataclasses import replace

            config = replace(config, dashboard_port=args.port)
        serve(db, config)
    elif args.command == "backup":
        args.destination.parent.mkdir(parents=True, exist_ok=True)
        source = db.connect()
        destination = sqlite3.connect(args.destination)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        print(f"Database backup written: {args.destination}")
    elif args.command == "analytics-import":
        print(f"Imported {import_csv(db, args.csv_file)} analytics row(s).")
    elif args.command == "analytics-report":
        print(json.dumps(analytics_report(db), indent=2))
    elif args.command == "upload":
        job = get_job(db, args.job_id)
        if job["status"] != "approved" or not approval_is_current(
            db, args.job_id, Path(job["output_dir"])
        ):
            raise ValueError("Publishing requires current approval for the exact package.")
        upload_approved_video(config, args.job_id)
    else:
        raise ValueError(f"Unhandled command: {args.command}")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(run(args))
    except (ConfigurationError, ValueError, KeyError, RuntimeError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
