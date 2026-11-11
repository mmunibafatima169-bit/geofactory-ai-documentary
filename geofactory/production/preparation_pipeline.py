"""Connect PreproductionPlan scenes to fail-closed preparation jobs."""

from __future__ import annotations

from dataclasses import asdict

from geofactory.production.capabilities import Capability
from geofactory.production.engine_adapters import PreparationJob, build_preparation_job
from geofactory.production.models import PreproductionPlan


def plan_preparation(plan: PreproductionPlan, capabilities: dict[str, Capability]) -> tuple[PreparationJob, ...]:
    """Return jobs only; never execute acquisition, scene building or rendering."""
    plan.validate()
    jobs = []
    for scene in plan.scenes:
        engines = [scene.preparation_engine]
        if scene.motion_engine != scene.preparation_engine:
            engines.append(scene.motion_engine)
        for engine in engines:
            capability = capabilities.get(engine, Capability(engine, False, False, None, None, "No runtime capability was registered"))
            jobs.append(build_preparation_job(scene.scene_id, engine, capability))
    return tuple(jobs)


def preparation_summary(jobs: tuple[PreparationJob, ...]) -> dict:
    return {
        "job_count": len(jobs),
        "executable_count": sum(job.executable for job in jobs),
        "blocked_count": sum(not job.executable for job in jobs),
        "jobs": [asdict(job) for job in jobs],
        "execution_performed": False,
        "video_rendered": False,
    }
