# CHANGELOG.md — Verified Historical Changes

All entries reference actual commits, test results, or file evidence. No invented dates or claims.

---

## [Unreleased] - 2026-11-12 (Branch: feature/documentary-planner, Commit: c8c7425)

### Cinematic Scene Transitions (This Session)

#### Documentary Renderer
- **ADDED**: Cinematic scene transitions using Visual Director's transition specifications
  - Implemented `_build_transition_filter()` helper generating FFmpeg xfade/fade filters
  - Supported transitions: `zoom_punch` (zoom in/out punch), `wipe_map` (directional wipe), `dip_to_black` (fade to black), `crossfade` (smooth dissolve), `cut` (hard cut)
  - Transition duration scales with segment length: max 1.5s, 15% of segment duration
  - Renderer reads `transition` field from ScenePlan (set by Visual Director per scene)
  - Evidence: `geofactory/media/documentary_renderer.py` lines 70-130

#### Test Infrastructure
- **ADDED**: Transition filter unit tests (`tests/test_transitions.py`)
  - 8 tests covering all transition types: zoom_punch, wipe_map, dip_to_black, crossfade, cut, unknown
  - Tests verify filter structure, duration scaling, offset calculation
  - All tests PASS without requiring FFmpeg/PIL
  - Evidence: `tests/test_transitions.py` — 8 PASS

### Critical Fixes (Previous Session)

#### Pipeline Orchestrator
- **FIXED**: Job-status transitions now reconcile with `core/jobs.py` STATUSES/TRANSITIONS
  - Added `_transition_job_safely()` helper that validates transitions before applying
  - Removed invalid statuses: "planning", "narrating", "qa_review"
  - Maps pipeline stages to valid job statuses: researching, scripting, awaiting_review, rendering, awaiting_approval, qa_failed
- **FIXED**: Pipeline never moves to `awaiting_approval` when QA reports `approval_blocked`
  - Final QA check runs after all stages; transitions to `qa_failed` if blocked, `awaiting_approval` only if clean
  - Evidence: `run_full_pipeline()` in `geofactory/pipeline/orchestrator.py` lines 380-395

#### Documentary Planner Validation
- **FIXED**: Invalid documentary plans now fail before rendering
  - Added `InvalidPlanError` exception class
  - `run_plan_stage()` raises on critical validation errors (duration bounds, chapter structure, missing claims, no scenes)
  - Warnings (word count, asset coverage) still allow continuation but are logged
  - Evidence: `geofactory/pipeline/orchestrator.py` lines 185-210

#### Factual Verifier Integration
- **ADDED**: `FACT_CHECK` pipeline stage between script and plan
  - Runs `verify_fact_ledger()` on source_ledger.json + script narration
  - Blocks pipeline on critical findings (conflicting numbers, unsourced display numbers, missing claim sources)
  - Flags `human_verification_needed` for unverified claims (allows continuation but logs warning)
  - Evidence: `run_fact_check_stage()` in `geofactory/pipeline/orchestrator.py` lines 140-180

#### Shorts Generator
- **FIXED**: Shorts now preserve chronological story flow
  - Scenes selected as contiguous window from documentary narrative (not reordered by engagement score)
  - Best-scoring window found but chronological order maintained
  - Evidence: `create_shorts_plan()` in `geofactory/media/shorts_generator.py` lines 140-210
- **FIXED**: Narration and subtitles synchronized to selected scenes
  - Parses original SRT, maps segments to shorts timeline using proportional timing
  - Generates `shorts_subtitles.srt` with correct timing for selected scenes
  - Evidence: `_build_subtitle_segments_for_shorts()` and `_write_shorts_srt()` in `geofactory/media/shorts_generator.py`
- **FIXED**: Actual output duration validated
  - Returns `actual_duration` in stage result, measured via FFprobe on output file
  - Evidence: `run_shorts_stage()` in `geofactory/pipeline/orchestrator.py` lines 290-300

### Test Infrastructure (Previous Session)
- **ADDED**: FFmpeg integration tests with synthetic fixtures (`tests/test_render_integration.py`)
  - 11 tests covering video_editor, documentary_renderer, shorts_generator
  - Uses FFmpeg lavfi (testsrc, sine) for synthetic video/audio fixtures
  - Tests properly skipped when FFmpeg/PIL unavailable (sandbox limitation)
  - Tests verify output file exists, correct duration, valid container, stream types

### New Modules Added (Since 49d22d7)
- `geofactory/pipeline/orchestrator.py` - 8-stage pipeline with checkpoint/resume
- `geofactory/media/documentary_renderer.py` - Per-scene FFmpeg rendering from plan
- `geofactory/media/shorts_generator.py` - YouTube Shorts with synced subtitles
- `geofactory/studio/documentary_planner.py` - Chapter planning, scene manifest generation
- `tests/test_render_integration.py` - FFmpeg integration tests with synthetic fixtures
- `tests/test_transitions.py` - Cinematic transition filter unit tests

### New CLI Commands
- `plan-documentary JOB_ID --duration 600` - Creates documentary_plan.json, scene_manifest.json, asset_allocations.json
- `render-documentary JOB_ID --output final.mp4` - Renders from plan with per-scene asset mapping
- `shorts JOB_ID --duration 45 --hook "..."` - Generates YouTube Shorts (9:16 vertical)
- `produce JOB_ID --resume --duration 600 --shorts-duration 45` - Full automated pipeline

### Tests Added
- `tests/test_documentary_planner.py` - 13 tests (all PASS)
- `tests/test_documentary_renderer.py` - 6 tests (skipped: needs PIL)
- `tests/test_shorts_generator.py` - 8 tests (skipped: needs PIL)
- `tests/test_pipeline_orchestrator.py` - 7 tests (skipped: needs PIL)
- `tests/test_render_integration.py` - 11 tests (skipped: needs FFmpeg/PIL)
- `tests/test_transitions.py` - 8 tests (all PASS) — **NEW THIS SESSION**

### Cleanup
- Removed 6 duplicate continuity docs from `geofactory/` subfolder (kept repo-root canonical copies)
- Corrected continuity documents using actual Git history (baseline commit 188e0a4 NOT FOUND)

---

## [2026-11-12] - Commit 49d22d7 (main branch)

### Studio v2 Quality Upgrade
- Rendered 60-second Venice documentary sample v2 at 1920×1080p30
- Licensed real footage: CC BY-SA 3.0 gondolas, public domain 1896 archival film
- Animated maps, technical cross-sections, sourced charts
- Original music/SFX, soft subtitles
- Decoded-video QA: 0 freeze warnings, 0 subtitle warnings, factual display gate passing

### Studio Layer Merge (Arena)
- Merge commit: `dc85cdd` (Studio layer: multi-engine architecture with Visual Director)
- Added: `geofactory/studio/`, `studio/remotion/`, Blender/Manim adapters
- Visual Director v2: ranked rules + variety penalty
- Editorial QA v2: decoded-video checks
- Scene manifest: validated per-scene production plan
- Design tokens: shared palette/typography/camera/transition/sound presets

---

## [2026-11-11] - Commit c3acccd

### Visual Storytelling Upgrade
- Paced stills, motion variety, map montage
- Ken Burns with 4 alternating motions
- Video-first rendering (stock clips at actual duration)

---

## [2026-11-10] - Commit 4e2d140

### Dry-run Test Path Resolution
- Fixed config semantics for test paths

---

## [2026-11-09] - Commit 52127e8

### Thumbnail Engine Tuning
- Tuned to measured reference study

---

## [2026-11-08] - Commit bd7be89

### Gemini Video Structure Analysis CLI
- Added CLI for video structure analysis

---

## [2026-11-07] - Commit ee0efd5

### Thumbnail Scoring & Reference Analysis
- Improved thumbnail scoring
- Documented reference analysis

---

## [2026-11-06] - Commit 5d523ae

### Map Animation & Thumbnail Engines
- Added map animation engine (Natural Earth)
- Added thumbnail engine (3 concepts, heuristic scores)

---

## [2026-11-05] - Commit 05e50ce

### Optional Providers
- Added optional Groq and stock media providers (Pexels, Pixabay)

---

## [2026-11-04] - Commit a73d20b

### Post-render Memory Snapshot
- Record memory snapshot after render

