#!/usr/bin/env python3
"""Emit the scene manifest + editorial report for the 60-second sample.

Builds a validated SceneManifest from the same scene table the assembler
uses, then runs the studio editorial QA (reuse / static-wall / objective
agreement) and a per-scene contact sheet against the rendered file.

    python3 studio/sample60_manifest.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from geofactory.studio.editorial_qa import build_report              # noqa: E402
from geofactory.studio.factual_verifier import verify_fact_ledger     # noqa: E402
from geofactory.studio.scene_manifest import SceneManifest, ScenePlan  # noqa: E402
from studio.assemble_sample60 import SCENES, XFADE                    # noqa: E402

OBJECTIVES = {
    "S1ColdOpen": ("cold_open", "globe_zoom_title", "push_in", ["kinetic_headline", "location_label"]),
    "S2LagoonMap": ("map_context", "map_highlight_arrows", "pan_right", ["inlet_labels", "lower_third"]),
    "S3Foundations": ("engineering_demo", "cross_section_build", "pan_down", ["strata_callouts", "stat_headline"]),
    "S4Stats": ("data_chart", "animated_bars_countup", "static", ["axis_labels", "headline_number"]),
    "S5Mose": ("engineering_demo", "mechanism_animation", "static", ["part_callouts", "level_indicator"]),
    "S6Closing": ("comparison_montage", "world_zoom_markers", "pull_back", ["city_labels", "closing_title"]),
}
TRANSITIONS = ["zoom_punch", "cut", "dip_to_black", "cut", "dip_to_black", "cut"]


def build_manifest() -> SceneManifest:
    scenes: list[ScenePlan] = []
    cursor = 0.0
    for index, scene in enumerate(SCENES):
        objective, animation, camera, overlays = OBJECTIVES[scene.composition]
        assets = [f"remotion://{scene.composition}"]
        if scene.composition == "S1ColdOpen":
            assets.append(str(REPO / "studio/remotion/public/footage/gondolas.webm"))
        if scene.composition == "S4Stats":
            assets.append(str(REPO / "studio/remotion/public/footage/venice-1896.webm"))
        scenes.append(ScenePlan(
            scene_id=scene.scene_id,
            narration=scene.narration,
            start_s=round(cursor, 3),
            end_s=round(cursor + scene.seconds, 3),
            visual_objective=objective,
            engine=scene.engine,
            animation_type=animation,
            camera=camera,
            text_overlays=overlays,
            transition=TRANSITIONS[index],
            sound_fx=[scene.sfx] if scene.sfx else [],
            assets=assets,
            source_ids=[],
            rationale=(
                "Visual Director: narration beat is "
                f"{objective.replace('_', ' ')}; rendered with {scene.engine} "
                f"using {animation.replace('_', ' ')} and a {camera.replace('_', ' ')} camera."
            ),
        ))
        cursor += scene.seconds - XFADE
    manifest = SceneManifest(
        job_id="venice-sample-60s",
        title="Why Is Venice Sinking? — 60-second studio sample",
        fps=30, width=1920, height=1080, scenes=scenes,
    )
    manifest.validate()
    return manifest


def main() -> int:
    out_dir = REPO / "studio/remotion/out"
    manifest = build_manifest()
    manifest_path = out_dir / "scene_manifest.json"
    manifest.save(manifest_path)

    video = out_dir / "venice_sample_60s_v2.mp4"
    subtitles = out_dir / "work60_v2/subtitles.srt"
    narration = " ".join(scene.narration for scene in SCENES)
    displayed_text = "118 islands · 90 cm · 194 cm · 300 cm design limit · 78 gates"
    fact_report = verify_fact_ledger(
        REPO / "studio/sample60_facts.json",
        displayed_text=displayed_text,
        narration_text=narration,
    )
    (out_dir / "factual_report.json").write_text(
        json.dumps(fact_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = build_report(
        manifest,
        video=video if video.is_file() else None,
        work_dir=out_dir,
        ffmpeg=str(REPO / ".tools/ffmpeg"),
        subtitles=subtitles if subtitles.is_file() else None,
        fact_report=fact_report,
    )
    report_path = out_dir / "editorial_report_v2.json"
    report.save(report_path)

    print(json.dumps({
        "scene_manifest": str(manifest_path),
        "editorial_report": str(report_path),
        "factual_report": str(out_dir / "factual_report.json"),
        "scenes": len(manifest.scenes),
        "runtime_s": round(manifest.scenes[-1].end_s, 2),
        "critical_findings": report.critical_count,
        "factual_approval_blocked": fact_report["approval_blocked"],
        "static_wall_max_s": report.static_wall_max_s,
        "repeated_assets": report.repeated_assets,
        "contact_sheet": report.contact_sheet,
        "findings": [f.to_dict() for f in report.findings],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
