"""
Documentary Planner: End-to-end script-to-scene pipeline for 8-15 minute documentaries.

This module bridges the script agent and Visual Director, enforcing the required
chapter structure, planning scenes across the full duration with proper pacing,
and integrating asset selection for each scene.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from geofactory.agents.script_agent import generate_evidence_script, write_script_preview
from geofactory.core.config import FactoryConfig
from geofactory.core.database import Database
from geofactory.core.jobs import get_job
from geofactory.media.asset_manager import ALLOWED_MEDIA_LICENSES
from geofactory.studio.asset_selector import VisualAssetCandidate, score_candidate, probe_asset
from geofactory.studio.scene_manifest import SceneManifest, ScenePlan
from geofactory.studio.visual_director import plan_scenes, Segment


# Required chapter structure per GeoFactory specification
REQUIRED_CHAPTERS = [
    "question",      # The hook - surprising viewer question within first 15s
    "context",       # Geographic context, location, terrain, climate
    "cause",         # Why it happens - mechanisms, history, geography
    "consequence",   # What happens - impacts, current state, evidence
    "bigger_picture", # Broader context - comparisons, global patterns
    "conclusion",    # Return to viewer question, no unsupported superlatives
]

CHAPTER_DISPLAY_NAMES = {
    "question": "The Question",
    "context": "Geographic Context",
    "cause": "Causes & Mechanisms",
    "consequence": "Consequences & Evidence",
    "bigger_picture": "The Bigger Picture",
    "conclusion": "Conclusion",
}

# Target duration for professional documentaries (seconds)
MIN_DURATION_S = 480   # 8 minutes
MAX_DURATION_S = 900   # 15 minutes
TARGET_DURATION_S = 600  # 10 minutes default


@dataclass
class ChapterPlan:
    """Planned chapter with timing and content guidance."""
    key: str
    title: str
    start_s: float
    end_s: float
    narration_text: str = ""
    visual_directions: list[str] = field(default_factory=list)
    required_claim_ids: list[str] = field(default_factory=list)


@dataclass
class DocumentaryPlan:
    """Complete documentary plan with chapters, scenes, and asset allocations."""
    job_id: str
    title: str
    topic: str
    question: str
    target_duration_s: float
    chapters: list[ChapterPlan]
    scene_manifest: SceneManifest
    asset_allocations: dict[str, list[VisualAssetCandidate]]  # scene_id -> assets
    total_narration_words: int
    estimated_render_duration_s: float


def parse_script_chapters(script_path: Path) -> tuple[list[str], str, list[str]]:
    """
    Parse a script.md file to extract chapter titles, full narration text, and visual directions.
    Returns (chapter_titles, narration_text, visual_directions).
    """
    content = script_path.read_text(encoding="utf-8")
    
    # Extract narration section
    narration_match = re.search(r"## Narration[^\n]*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if narration_match:
        narration_text = narration_match.group(1).strip()
        # Strip word count header if present (e.g., "(1500 words)")
        narration_text = re.sub(r"^\(\d+\s+words\)\s*\n*", "", narration_text)
    else:
        # Fallback: try to find narration after the opening
        parts = content.split("## Narration")
        narration_text = parts[1].split("## ")[0].strip() if len(parts) > 1 else ""
    
    # Extract chapters
    chapters_match = re.search(r"## Chapters\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    chapter_titles = []
    if chapters_match:
        chapter_lines = chapters_match.group(1).strip().split("\n")
        for line in chapter_lines:
            line = line.strip()
            if re.match(r"^\d+\.\s+", line):
                title = re.sub(r"^\d+\.\s+", "", line)
                chapter_titles.append(title)
    
    # Extract scene plan
    scene_plan_match = re.search(r"## Scene plan\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    visual_directions = []
    if scene_plan_match:
        scene_lines = scene_plan_match.group(1).strip().split("\n")
        for line in scene_lines:
            line = line.strip()
            if line.startswith("- **"):
                # Extract visual direction after the bold title
                match = re.search(r"-\s*\*\*(.+?)\*\*\s+(.+)", line)
                if match:
                    visual_directions.append(match.group(2).strip())
    
    # If we don't have 6 chapters, create defaults
    if len(chapter_titles) < 6:
        chapter_titles = [CHAPTER_DISPLAY_NAMES[k] for k in REQUIRED_CHAPTERS]
    
    return chapter_titles, narration_text, visual_directions


def allocate_chapter_time(
    narration_text: str,
    target_duration_s: float,
    chapter_titles: list[str]
) -> list[ChapterPlan]:
    """
    Allocate time across chapters based on narration word count per chapter.
    Enforces the 6-chapter structure with appropriate pacing.
    """
    # Split narration into sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration_text.strip()) if s.strip()]
    if not sentences:
        # Fallback: equal allocation
        chapter_duration = target_duration_s / 6
        chapters = []
        cursor = 0.0
        for i, key in enumerate(REQUIRED_CHAPTERS):
            chapters.append(ChapterPlan(
                key=key,
                title=CHAPTER_DISPLAY_NAMES[key],
                start_s=cursor,
                end_s=cursor + chapter_duration,
            ))
            cursor += chapter_duration
        return chapters
    
    # Weight: question chapter gets ~10%, conclusion ~10%, others ~20% each
    weights = {
        "question": 0.10,
        "context": 0.20,
        "cause": 0.22,
        "consequence": 0.22,
        "bigger_picture": 0.16,
        "conclusion": 0.10,
    }
    
    # Distribute sentences proportionally
    total_words = len(narration_text.split())
    words_per_second = total_words / target_duration_s if target_duration_s > 0 else 2.7
    
    chapters = []
    cursor = 0.0
    sentence_idx = 0
    
    for i, key in enumerate(REQUIRED_CHAPTERS):
        chapter_weight = weights[key]
        chapter_words = int(total_words * chapter_weight)
        chapter_duration = chapter_words / words_per_second if words_per_second > 0 else target_duration_s / 6
        
        # Collect sentences for this chapter
        chapter_sentences = []
        chapter_word_count = 0
        while sentence_idx < len(sentences) and chapter_word_count < chapter_words:
            chapter_sentences.append(sentences[sentence_idx])
            chapter_word_count += len(sentences[sentence_idx].split())
            sentence_idx += 1
        
        # Ensure we don't run out of sentences early
        if i == len(REQUIRED_CHAPTERS) - 1 and sentence_idx < len(sentences):
            chapter_sentences.extend(sentences[sentence_idx:])
        
        chapter_text = " ".join(chapter_sentences)
        chapters.append(ChapterPlan(
            key=key,
            title=CHAPTER_DISPLAY_NAMES[key],
            start_s=cursor,
            end_s=cursor + chapter_duration,
            narration_text=chapter_text,
        ))
        cursor += chapter_duration
    
    # Adjust last chapter to hit exact target
    if chapters:
        chapters[-1].end_s = target_duration_s
    
    return chapters


def assign_visual_directions_to_chapters(
    chapters: list[ChapterPlan],
    visual_directions: list[str]
) -> None:
    """Distribute visual directions from scene plan across chapters."""
    if not visual_directions:
        # Default visual directions per chapter type
        defaults = {
            "question": ["Opening map zoom to location", "Kinetic title card"],
            "context": ["Terrain/relief map with labels", "Satellite imagery context"],
            "cause": ["Animated diagram of mechanism", "Cross-section or data chart"],
            "consequence": ["Before/after comparison", "Impact visualization on map"],
            "bigger_picture": ["Multi-location comparison montage", "Global pattern map"],
            "conclusion": ["Return to opening map", "Final title card with question"],
        }
        for chapter in chapters:
            chapter.visual_directions = defaults.get(chapter.key, ["Map context", "Licensed footage"])
    else:
        # Distribute provided directions across chapters
        per_chapter = max(1, len(visual_directions) // len(chapters))
        idx = 0
        for chapter in chapters:
            chapter.visual_directions = visual_directions[idx:idx + per_chapter]
            idx += per_chapter
        # Any remaining go to last chapter
        if idx < len(visual_directions):
            chapters[-1].visual_directions.extend(visual_directions[idx:])


def extract_claim_ids_from_narration(narration: str) -> list[str]:
    """Extract all claim IDs from narration text."""
    return re.findall(r"\[(clm-[a-z0-9-]+)\]", narration)


def create_narration_segments(chapters: list[ChapterPlan]) -> list[Segment]:
    """
    Create narration segments from chapter plans with proper granularity.
    Distributes each chapter's sentences across its allocated time range,
    creating segments of at most MAX_SEGMENT_DURATION seconds each.
    
    This ensures compatibility with Visual Director's MAX_SCENE_SECONDS (22s)
    and SceneManifest's 40s scene limit.
    """
    MAX_SEGMENT_DURATION = 20.0  # Must be <= Visual Director's MAX_SCENE_SECONDS (22.0)
    
    all_segments = []
    
    for chapter in chapters:
        if not chapter.narration_text.strip():
            # Empty chapter - create segments to fill the time
            remaining_time = chapter.end_s - chapter.start_s
            if remaining_time > 0:
                # Split into segments of MAX_SEGMENT_DURATION
                num_segments = max(1, int(remaining_time / MAX_SEGMENT_DURATION) + (1 if remaining_time % MAX_SEGMENT_DURATION > 0 else 0))
                seg_duration = remaining_time / num_segments
                for i in range(num_segments):
                    seg_start = chapter.start_s + i * seg_duration
                    seg_end = min(chapter.start_s + (i + 1) * seg_duration, chapter.end_s)
                    all_segments.append(Segment(
                        text=f"[Chapter: {chapter.title}]",
                        start_s=seg_start,
                        end_s=seg_end
                    ))
            continue
        
        # Split chapter narration into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", chapter.narration_text.strip()) if s.strip()]
        if not sentences:
            continue
        
        chapter_duration = chapter.end_s - chapter.start_s
        if chapter_duration <= 0:
            continue
        
        # Calculate the minimum number of segments needed to keep each <= MAX_SEGMENT_DURATION
        min_segments = max(1, int((chapter_duration + MAX_SEGMENT_DURATION - 1) // MAX_SEGMENT_DURATION))
        
        # If we have fewer sentences than minimum segments, we'll need to repeat/distribute
        # We create exactly min_segments segments and distribute sentences across them
        num_segments = max(min_segments, 1)
        
        # Target duration per segment
        target_seg_duration = chapter_duration / num_segments
        
        # Distribute sentences across segments as evenly as possible
        # Each segment gets at least 1 sentence if we have enough, otherwise some segments share
        if len(sentences) >= num_segments:
            # We have enough sentences - distribute them
            sentences_per_segment = len(sentences) / num_segments
            sentence_idx = 0
            
            for seg_idx in range(num_segments):
                seg_start = chapter.start_s + seg_idx * target_seg_duration
                seg_end = min(chapter.start_s + (seg_idx + 1) * target_seg_duration, chapter.end_s)
                
                # Calculate how many sentences this segment should get
                target_sentence_count = int(round((seg_idx + 1) * sentences_per_segment)) - int(round(seg_idx * sentences_per_segment))
                target_sentence_count = max(1, target_sentence_count)
                
                seg_sentences = sentences[sentence_idx:sentence_idx + target_sentence_count]
                sentence_idx += len(seg_sentences)
                
                # Handle last segment - take all remaining sentences
                if seg_idx == num_segments - 1:
                    seg_sentences.extend(sentences[sentence_idx:])
                
                segment_text = " ".join(seg_sentences) if seg_sentences else f"[Chapter: {chapter.title}]"
                
                all_segments.append(Segment(
                    text=segment_text,
                    start_s=seg_start,
                    end_s=seg_end
                ))
        else:
            # Fewer sentences than segments - some segments will share/repeat sentences
            # We cycle through sentences to fill all segments
            for seg_idx in range(num_segments):
                seg_start = chapter.start_s + seg_idx * target_seg_duration
                seg_end = min(chapter.start_s + (seg_idx + 1) * target_seg_duration, chapter.end_s)
                
                sentence = sentences[seg_idx % len(sentences)]
                
                all_segments.append(Segment(
                    text=sentence,
                    start_s=seg_start,
                    end_s=seg_end
                ))
    
    # Ensure segments are contiguous and cover the full duration
    if all_segments:
        # Adjust last segment to end exactly at the last chapter's end
        all_segments[-1] = Segment(
            text=all_segments[-1].text,
            start_s=all_segments[-1].start_s,
            end_s=chapters[-1].end_s
        )
    
    return all_segments if all_segments else [Segment("", 0.0, chapters[-1].end_s if chapters else 600.0)]


def build_documentary_plan(
    db: Database,
    job_id: str,
    config: FactoryConfig,
    script_path: Path,
    target_duration_s: float = TARGET_DURATION_S,
) -> DocumentaryPlan:
    """
    Build a complete documentary plan from a script file.
    This is the main entry point for the end-to-end pipeline.
    """
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    
    # Parse script
    chapter_titles, narration_text, visual_directions = parse_script_chapters(script_path)
    
    # Allocate time across chapters
    chapters = allocate_chapter_time(narration_text, target_duration_s, chapter_titles)
    
    # Assign visual directions
    assign_visual_directions_to_chapters(chapters, visual_directions)
    
    # Extract claim IDs for each chapter
    for chapter in chapters:
        chapter.required_claim_ids = extract_claim_ids_from_narration(chapter.narration_text)
    
    # Create narration segments for Visual Director using chapter-level granularity
    segments = create_narration_segments(chapters)
    
    # Determine available engines
    engines_available = {"ffmpeg"}
    repo_root = Path(__file__).resolve().parents[2]
    if (repo_root / "studio" / "remotion" / "package.json").is_file():
        engines_available.add("remotion")
    import shutil
    if shutil.which("blender"):
        engines_available.add("blender")
    
    # Generate scene manifest via Visual Director
    scene_manifest = plan_scenes(
        job_id=job_id,
        title=job["topic"],
        segments=segments,
        engines_available=engines_available,
        width=config.width,
        height=config.height,
        fps=30,
    )
    
    # Load registered assets for this job
    asset_allocations = allocate_assets_to_scenes(db, job_id, scene_manifest, config)
    
    # Calculate totals
    total_words = len(narration_text.split())
    estimated_render = scene_manifest.scenes[-1].end_s if scene_manifest.scenes else target_duration_s
    
    return DocumentaryPlan(
        job_id=job_id,
        title=job["topic"],
        topic=job["topic"],
        question=job["question"],
        target_duration_s=target_duration_s,
        chapters=chapters,
        scene_manifest=scene_manifest,
        asset_allocations=asset_allocations,
        total_narration_words=total_words,
        estimated_render_duration_s=estimated_render,
    )


def allocate_assets_to_scenes(
    db: Database,
    job_id: str,
    manifest: SceneManifest,
    config: FactoryConfig,
) -> dict[str, list[VisualAssetCandidate]]:
    """Match registered assets to scenes based on relevance."""
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT id, title, path, origin_url, creator, licence, licence_url,
                      attribution, commercial_use, file_sha256, media_type, retrieved_at
               FROM assets WHERE job_id = ?""",
            (job_id,),
        ).fetchall()
    
    candidates = []
    for row in rows:
        if row["commercial_use"] != 1 or row["licence"] not in ALLOWED_MEDIA_LICENSES:
            continue
        candidate = VisualAssetCandidate(
            asset_id=row["id"],
            title=row["title"] or "Untitled",
            description=row["attribution"],
            media_type=row["media_type"],
            source_page=row["origin_url"],
            download_url=row["origin_url"],
            creator=row["creator"],
            licence=row["licence"],
            licence_url=row["licence_url"] or "",
            accessed_at=row["retrieved_at"],
            local_path=row["path"],
        )
        # Probe for dimensions/duration
        try:
            probe_asset(candidate, config.ffprobe)
        except Exception:
            pass  # Keep candidate even if probe fails
        candidates.append(candidate)
    
    # Score candidates against each scene's narration
    allocations = {}
    previous_titles = []
    for scene in manifest.scenes:
        scored = []
        for candidate in candidates:
            if candidate.media_type not in ("image", "video"):
                continue
            try:
                score = score_candidate(scene.narration, candidate, previous_titles=previous_titles)
                if score.overall >= 40:  # Minimum threshold
                    scored.append((score.overall, candidate))
            except Exception:
                continue
        
        scored.sort(key=lambda x: x[0], reverse=True)
        allocations[scene.scene_id] = [c for _, c in scored[:3]]  # Top 3 per scene
        if allocations[scene.scene_id]:
            previous_titles.append(allocations[scene.scene_id][0].title)
    
    return allocations


def write_documentary_plan(plan: DocumentaryPlan, output_dir: Path) -> None:
    """Write the complete documentary plan to package directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write scene manifest
    manifest_path = output_dir / "scene_manifest.json"
    plan.scene_manifest.save(manifest_path)
    
    # Write chapter plan
    chapter_data = {
        "job_id": plan.job_id,
        "title": plan.title,
        "topic": plan.topic,
        "question": plan.question,
        "target_duration_s": plan.target_duration_s,
        "total_narration_words": plan.total_narration_words,
        "estimated_render_duration_s": plan.estimated_render_duration_s,
        "chapters": [
            {
                "key": c.key,
                "title": c.title,
                "start_s": c.start_s,
                "end_s": c.end_s,
                "duration_s": c.end_s - c.start_s,
                "narration_word_count": len(c.narration_text.split()) if c.narration_text else 0,
                "visual_directions": c.visual_directions,
                "required_claim_ids": c.required_claim_ids,
            }
            for c in plan.chapters
        ],
    }
    (output_dir / "documentary_plan.json").write_text(
        json.dumps(chapter_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    
    # Write asset allocations
    asset_data = {
        "job_id": plan.job_id,
        "allocations": {
            scene_id: [c.to_dict() for c in assets]
            for scene_id, assets in plan.asset_allocations.items()
        },
    }
    (output_dir / "asset_allocations.json").write_text(
        json.dumps(asset_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_documentary_plan(plan: DocumentaryPlan) -> list[str]:
    """Validate the documentary plan for production readiness."""
    errors = []
    
    # Check duration
    if plan.estimated_render_duration_s < MIN_DURATION_S:
        errors.append(f"Estimated duration {plan.estimated_render_duration_s:.0f}s below minimum {MIN_DURATION_S}s (8 min)")
    if plan.estimated_render_duration_s > MAX_DURATION_S:
        errors.append(f"Estimated duration {plan.estimated_render_duration_s:.0f}s exceeds maximum {MAX_DURATION_S}s (15 min)")
    
    # Check chapter structure
    if len(plan.chapters) != 6:
        errors.append(f"Expected 6 chapters, got {len(plan.chapters)}")
    else:
        for i, (expected_key, chapter) in enumerate(zip(REQUIRED_CHAPTERS, plan.chapters)):
            if chapter.key != expected_key:
                errors.append(f"Chapter {i+1} should be '{expected_key}', got '{chapter.key}'")
    
    # Check word count
    if plan.total_narration_words < 1200:
        errors.append(f"Narration only {plan.total_narration_words} words, minimum 1200 for 8-15 min")
    if plan.total_narration_words > 3000:
        errors.append(f"Narration {plan.total_narration_words} words exceeds practical maximum for 15 min")
    
    # Check claim coverage
    all_claim_ids = set()
    for chapter in plan.chapters:
        all_claim_ids.update(chapter.required_claim_ids)
    if not all_claim_ids:
        errors.append("No claim IDs found in narration - factual claims must be cited")
    
    # Check scene manifest
    if not plan.scene_manifest.scenes:
        errors.append("Scene manifest has no scenes")
    
    # Check asset coverage
    scenes_without_assets = [
        s.scene_id for s in plan.scene_manifest.scenes
        if not plan.asset_allocations.get(s.scene_id)
    ]
    if scenes_without_assets and len(scenes_without_assets) > len(plan.scene_manifest.scenes) * 0.5:
        errors.append(f"Too many scenes without asset allocations: {len(scenes_without_assets)}/{len(plan.scene_manifest.scenes)}")
    
    return errors


# CLI integration function
def run_documentary_plan(
    db: Database,
    job_id: str,
    config: FactoryConfig,
    target_duration_s: float = TARGET_DURATION_S,
) -> DocumentaryPlan:
    """CLI entry point: build documentary plan for a job."""
    job = get_job(db, job_id)
    package = Path(job["output_dir"])
    
    # Find script file
    script_path = package / "script.md"
    if not script_path.is_file():
        raise FileNotFoundError(f"Script not found at {script_path}. Run 'script' command first.")
    
    # Build plan
    plan = build_documentary_plan(db, job_id, config, script_path, target_duration_s)
    
    # Validate
    errors = validate_documentary_plan(plan)
    if errors:
        print("Documentary plan validation warnings:")
        for err in errors:
            print(f"  - {err}")
    
    # Write outputs
    write_documentary_plan(plan, package)
    
    print(f"Documentary plan written to {package}")
    print(f"  Target duration: {plan.target_duration_s/60:.1f} min")
    print(f"  Estimated render: {plan.estimated_render_duration_s/60:.1f} min")
    print(f"  Narration words: {plan.total_narration_words}")
    print(f"  Scenes: {len(plan.scene_manifest.scenes)}")
    print(f"  Chapters: {len(plan.chapters)}")
    
    return plan
