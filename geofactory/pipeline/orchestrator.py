"""
Pipeline Orchestrator: End-to-end automated documentary production.

Chains: research → script → plan-documentary → narrate → render-documentary → shorts → qa
Supports checkpoint/resume for fault tolerance.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.core.jobs import (
    create_job, get_job, transition_job, list_jobs, package_digest
)
from geofactory.agents.research_agent import (
    discover_wikipedia_sources, export_ledger, import_ledger
)
from geofactory.agents.script_agent import generate_evidence_script, write_script_preview
from geofactory.media.asset_manager import (
    export_asset_ledger, search_and_download_commons, write_attribution_report
)
from geofactory.media.tts_engine import synthesize, write_text_only_narration
from geofactory.studio.documentary_planner import run_documentary_plan, validate_documentary_plan
from geofactory.media.documentary_renderer import render_documentary_from_plan
from geofactory.media.shorts_generator import generate_shorts_from_documentary
from geofactory.quality.qa_engine import run_qa


class PipelineStage(str, Enum):
    RESEARCH = "research"
    SCRIPT = "script"
    PLAN = "plan"
    NARRATE = "narrate"
    RENDER = "render"
    SHORTS = "shorts"
    QA = "qa"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PipelineState:
    """Current state of the pipeline for a job."""
    job_id: str
    current_stage: PipelineStage = PipelineStage.RESEARCH
    completed_stages: list[PipelineStage] = field(default_factory=list)
    stage_timings: dict[str, float] = field(default_factory=dict)
    stage_errors: dict[str, str] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    config_overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "current_stage": self.current_stage.value,
            "completed_stages": [s.value for s in self.completed_stages],
            "stage_timings": self.stage_timings,
            "stage_errors": self.stage_errors,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "config_overrides": self.config_overrides,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineState":
        return cls(
            job_id=data["job_id"],
            current_stage=PipelineStage(data["current_stage"]),
            completed_stages=[PipelineStage(s) for s in data.get("completed_stages", [])],
            stage_timings=data.get("stage_timings", {}),
            stage_errors=data.get("stage_errors", {}),
            started_at=data.get("started_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            config_overrides=data.get("config_overrides", {}),
        )


class PipelineError(RuntimeError):
    """Raised when pipeline execution fails."""
    def __init__(self, stage: PipelineStage, message: str):
        self.stage = stage
        super().__init__(f"Pipeline failed at {stage.value}: {message}")


CHECKPOINT_FILE = "pipeline_state.json"


def load_pipeline_state(package_dir: Path) -> PipelineState | None:
    """Load pipeline state from checkpoint file."""
    checkpoint_path = package_dir / CHECKPOINT_FILE
    if not checkpoint_path.is_file():
        return None
    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        return PipelineState.from_dict(data)
    except Exception:
        return None


def save_pipeline_state(package_dir: Path, state: PipelineState) -> None:
    """Save pipeline state to checkpoint file."""
    state.updated_at = datetime.utcnow().isoformat()
    checkpoint_path = package_dir / CHECKPOINT_FILE
    checkpoint_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def run_stage_with_timing(stage: PipelineStage, func, *args, **kwargs) -> tuple[Any, float]:
    """Run a pipeline stage function with timing."""
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        return result, time.perf_counter() - start
    except Exception as e:
        elapsed = time.perf_counter() - start
        raise PipelineError(stage, f"{type(e).__name__}: {e}") from e


def run_research_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, int]:
    """Stage 1: Research - discover Wikipedia sources."""
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    
    # Use config overrides if provided
    query = state.config_overrides.get("research_query", job["topic"])
    limit = state.config_overrides.get("research_limit", 10)
    
    sources = discover_wikipedia_sources(db, job_id, query, limit=limit)
    package.mkdir(parents=True, exist_ok=True)
    export_ledger(db, job_id, package / "source_ledger.json")
    write_script_preview(db, job_id, package / "script.md")
    
    return {"sources_added": len(sources)}


def run_script_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, int]:
    """Stage 2: Script - generate evidence-based script."""
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    script_path = package / "script.md"
    
    if config.groq_api_key.strip() or config.local_llm_model.strip():
        words = generate_evidence_script(db, job_id, script_path, config)
        provider = "Groq" if config.groq_api_key.strip() else "local model"
    else:
        words = write_script_preview(db, job_id, script_path)
        provider = "evidence-aware draft"
    
    return {"words": words, "provider": provider}


def run_plan_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, Any]:
    """Stage 3: Plan - build documentary plan with chapters, scenes, assets."""
    target_duration = state.config_overrides.get("duration", 600.0)
    plan = run_documentary_plan(db, job_id, config, target_duration)
    errors = validate_documentary_plan(plan)
    return {
        "target_duration": target_duration,
        "estimated_render": plan.estimated_render_duration_s,
        "narration_words": plan.total_narration_words,
        "scenes": len(plan.scene_manifest.scenes),
        "chapters": len(plan.chapters),
        "validation_warnings": errors,
    }


def run_narrate_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, Any]:
    """Stage 4: Narrate - generate TTS narration and subtitles."""
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    script_path = package / "script.md"
    
    if not script_path.is_file():
        raise PipelineError(PipelineStage.NARRATE, "Script not found. Run script stage first.")
    
    # Extract narration from script
    content = script_path.read_text(encoding="utf-8")
    import re
    narration_match = re.search(r"## Narration[^\n]*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if narration_match:
        narration_text = narration_match.group(1).strip()
        narration_text = re.sub(r"^\(\d+\s+words\)\s*\n*", "", narration_text)
    else:
        narration_text = content.split("## Narration")[-1].split("## ")[0].strip()
    
    # Generate narration
    narration_path = package / "narration.wav"
    subtitles_path = package / "subtitles.srt"
    
    if config.tts_backend == "none":
        write_text_only_narration(narration_text, package / "narration.txt")
        duration = 0.0
    else:
        duration = synthesize(
            narration_text, narration_path, config,
            subtitle_destination=subtitles_path,
        )
    
    return {"duration": duration, "backend": config.tts_backend}


def run_render_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, Any]:
    """Stage 5: Render - produce full documentary video from plan."""
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    output_path = package / "final.mp4"
    
    render_documentary_from_plan(config, job_id, package, output_path)
    
    # Verify output
    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    
    return {"output": str(output_path), "size_mb": round(size_mb, 2)}


def run_shorts_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, Any]:
    """Stage 6: Shorts - generate YouTube Shorts from documentary."""
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    output_path = package / "shorts.mp4"
    
    target_duration = state.config_overrides.get("shorts_duration", 45.0)
    hook_text = state.config_overrides.get("shorts_hook")
    
    generate_shorts_from_documentary(
        config, job_id, package, output_path,
        target_duration=target_duration,
        hook_text=hook_text,
    )
    
    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    
    return {"output": str(output_path), "size_mb": round(size_mb, 2), "duration": target_duration}


def run_qa_stage(
    db: Database, job_id: str, config: FactoryConfig, state: PipelineState
) -> dict[str, Any]:
    """Stage 7: QA - run release-gate checks."""
    report = run_qa(db, job_id, config)
    return {
        "approval_blocked": report["approval_blocked"],
        "critical_failures": report["critical_failures"],
        "warnings": report["warnings"],
    }


STAGE_FUNCTIONS = {
    PipelineStage.RESEARCH: run_research_stage,
    PipelineStage.SCRIPT: run_script_stage,
    PipelineStage.PLAN: run_plan_stage,
    PipelineStage.NARRATE: run_narrate_stage,
    PipelineStage.RENDER: run_render_stage,
    PipelineStage.SHORTS: run_shorts_stage,
    PipelineStage.QA: run_qa_stage,
}

STAGE_ORDER = [
    PipelineStage.RESEARCH,
    PipelineStage.SCRIPT,
    PipelineStage.PLAN,
    PipelineStage.NARRATE,
    PipelineStage.RENDER,
    PipelineStage.SHORTS,
    PipelineStage.QA,
]


def run_full_pipeline(
    db: Database,
    job_id: str,
    config: FactoryConfig,
    *,
    resume: bool = False,
    config_overrides: dict[str, Any] | None = None,
) -> PipelineState:
    """
    Run the complete documentary production pipeline.
    
    Args:
        db: Database connection
        job_id: Job identifier
        config: Factory configuration
        resume: If True, resume from last checkpoint
        config_overrides: Optional config overrides per stage
    
    Returns:
        Final PipelineState
    """
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    package.mkdir(parents=True, exist_ok=True)
    
    # Load or create pipeline state
    if resume:
        state = load_pipeline_state(package)
        if state is None:
            raise PipelineError(PipelineStage.RESEARCH, "No checkpoint found to resume from")
        # Merge config overrides
        if config_overrides:
            state.config_overrides.update(config_overrides)
    else:
        state = PipelineState(job_id=job_id, config_overrides=config_overrides or {})
        # Initialize job if needed
        if job["status"] == "proposed":
            transition_job(db, job_id, "researching", "Pipeline started")
    
    # Determine starting stage
    start_idx = 0
    if resume and state.completed_stages:
        last_completed = state.completed_stages[-1]
        try:
            start_idx = STAGE_ORDER.index(last_completed) + 1
        except ValueError:
            start_idx = 0
    
    # Run stages
    for stage in STAGE_ORDER[start_idx:]:
        state.current_stage = stage
        save_pipeline_state(package, state)
        
        # Update job status
        status_map = {
            PipelineStage.RESEARCH: "researching",
            PipelineStage.SCRIPT: "scripting",
            PipelineStage.PLAN: "planning",
            PipelineStage.NARRATE: "narrating",
            PipelineStage.RENDER: "rendering",
            PipelineStage.SHORTS: "rendering",
            PipelineStage.QA: "qa_review",
        }
        transition_job(db, job_id, status_map.get(stage, "processing"), f"Running {stage.value} stage")
        
        # Run stage with timing
        try:
            func = STAGE_FUNCTIONS[stage]
            result, elapsed = run_stage_with_timing(stage, func, db, job_id, config, state)
            state.stage_timings[stage.value] = elapsed
            state.completed_stages.append(stage)
            state.stage_errors.pop(stage.value, None)
            save_pipeline_state(package, state)
            print(f"✅ {stage.value} completed in {elapsed:.1f}s")
        except PipelineError as e:
            state.stage_errors[stage.value] = str(e)
            save_pipeline_state(package, state)
            transition_job(db, job_id, "qa_failed", f"Pipeline failed at {stage.value}: {e}")
            raise
        except Exception as e:
            state.stage_errors[stage.value] = f"{type(e).__name__}: {e}"
            save_pipeline_state(package, state)
            transition_job(db, job_id, "qa_failed", f"Pipeline failed at {stage.value}: {e}")
            raise PipelineError(stage, str(e)) from e
    
    # Pipeline complete
    state.current_stage = PipelineStage.COMPLETE
    state.stage_timings["total"] = sum(state.stage_timings.values())
    save_pipeline_state(package, state)
    
    # Final QA already ran as last stage
    transition_job(db, job_id, "awaiting_approval", "Pipeline complete, awaiting approval")
    
    print(f"\n🎬 Pipeline complete in {state.stage_timings['total']:.1f}s total")
    for stage, timing in state.stage_timings.items():
        if stage != "total":
            print(f"  {stage}: {timing:.1f}s")
    
    return state


def run_pipeline_from_cli(
    config: FactoryConfig,
    job_id: str,
    *,
    resume: bool = False,
    duration: float = 600.0,
    shorts_duration: float = 45.0,
    shorts_hook: str | None = None,
    research_query: str | None = None,
    research_limit: int = 10,
) -> PipelineState:
    """CLI entry point for pipeline execution."""
    db = Database(config.database_path)
    
    overrides = {
        "duration": duration,
        "shorts_duration": shorts_duration,
        "research_limit": research_limit,
    }
    if shorts_hook:
        overrides["shorts_hook"] = shorts_hook
    if research_query:
        overrides["research_query"] = research_query
    
    return run_full_pipeline(db, job_id, config, resume=resume, config_overrides=overrides)
