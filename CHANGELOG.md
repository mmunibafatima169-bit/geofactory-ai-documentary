# CHANGELOG.md — Verified Historical Changes

All entries reference actual commits, test results, or file evidence. No invented dates or claims.

---

## [Unreleased] - 2026-11-15 (Branch: feature/documentary-planner, Commit: 90cad1d)

### Critical Fixes (This Session)

#### CLI Shadowed Import Fix (BUG 1)
- **FIXED**: `Database` and `Path` imported inside smoke handler shadowed module-level names, causing `UnboundLocalError` for all CLI commands
- **Fix**: Removed local `from pathlib import Path` imports (lines 1016, 1858) from `run()` function; moved smoke handler to separate `_cmd_smoke()` function with lazy imports at function start
- **Files**: `geofactory/cli.py`
- **Evidence**: `tests/test_cli_shadow_audit.py` — 3 PASS (AST-based audit)

#### Smoke Profile for Plan Validation (BUG 2)
- **FIXED**: Smoke test fixture (~88 words) fails production validation (min 1200 words, asset allocation gates)
- **Fix**: Added `profile` parameter to `validate_documentary_plan()` and `run_documentary_plan()`:
  - `profile="production"` (default): Full 8-15 min rules (1200-3000 words, claims, assets required)
  - `profile="smoke"`: Relaxed rules (min 50 words, no claim/asset requirements, 60-120s duration)
- **Files**: `geofactory/studio/documentary_planner.py`, `geofactory/cli.py` (passes `profile="smoke"`)
- **Evidence**: `tests/test_documentary_planner.py::test_profile_smoke_vs_production` — PASS

#### CI Pipefail Fix (BUG 3)
- **ci.yml**: Added `shell: bash` + `set -o pipefail` to test step; added `$GITHUB_STEP_SUMMARY` with failed tests list
- **smoke.yml**: Proper exit code capture with `set +e`/`set -e`; added `$GITHUB_STEP_SUMMARY` with smoke.log tail and summary.json
- **Files**: `.github/workflows/ci.yml`, `.github/workflows/smoke.yml`

#### CLI Regression Test (BUG 1c)
- **ADDED**: `tests/test_cli_smoke_regression.py`
- Tests: `--help`, `smoke --help`, `init` in temp dir - all exit 0 without PIL
- **Files**: `tests/test_cli_smoke_regression.py`

#### Shorts FFmpeg Filtergraph Fix (BUG 1 - new)
- **FIXED**: "Simple and complex filtering cannot be used together" error in Shorts generator
- **Fix**: Moved scale/crop/setsar from `-vf` into `filter_complex` with `[vfinal]` label; changed `-map "[vout]"` to `-map "[vfinal]"`
- **File**: `geofactory/media/shorts_generator.py`

#### Checkpoint Directory Fix (BUG 2 - new)
- **FIXED**: `FileNotFoundError .../pipeline_state.json` - parent dir didn't exist
- **Fix**: Added `package_dir.mkdir(parents=True, exist_ok=True)` in `save_pipeline_state()`
- **File**: `geofactory/pipeline/orchestrator.py`

#### Orchestrator Tests Fix (BUG 3 - new)
- **test_stage_order**: Updated to include `FACT_CHECK` stage in expected order
- **test_run_full_pipeline_research_only**: Restored with proper mocking of `STAGE_FUNCTIONS` registry
- **Files**: `tests/test_pipeline_orchestrator.py`

#### Error-Message Drift Fix (BUG 4 - new)
- Changed fragile exact-string assertions to exception type + key substring checks
- **Files**: `tests/test_shorts_generator.py`, `tests/test_documentary_renderer.py`

#### Licence Fixture Fix (BUG 5 - new)
- Changed "Test License" to "CC0-1.0" in synthetic video clip test
- **File**: `tests/test_render_integration.py`

#### Scene Priority Test Fix (BUG 6 - new)
- Updated assertion to match actual algorithm behavior (contiguous window selection in chronological order)
- **File**: `tests/test_shorts_generator.py`

#### Profile Test Added (BUG 7 - new)
- Permanent test showing production profile rejects 88-word plan, smoke profile accepts
- **File**: `tests/test_documentary_planner.py`

#### Thumbnail Engine Lazy-PIL (A1)
- **ADDED**: `_lazy_pil()` helper; all 6 functions now import PIL lazily at function start
- Module loads without PIL installed
- **File**: `geofactory/media/thumbnail_engine.py`

#### Smoke Ledger Path & Import Fix (A2)
- Changed ledger path to `Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "singapore_ledger.json"`
- Used `import_ledger_data()` for dict instead of `import_ledger()` for Path
- **File**: `geofactory/cli.py`

#### CLI Smoke Regression Test Env Fix (A3)
- Added `PYTHONPATH=/root/geofactory-ai-documentary` to subprocess env
- **File**: `tests/test_cli_smoke_regression.py`

#### Shadow Audit Test Created
- **ADDED**: `tests/test_cli_shadow_audit.py` - AST-based audit enforcing no shadowed imports in `run()` and lazy imports at start in `_cmd_smoke()`

#### Pipeline Test PIL Check Fix
- **FIXED**: Runtime `PIL_AVAILABLE` check replacing broken import-time check that caused false `PIPELINE_MODULES_AVAILABLE = True`
- **File**: `tests/test_pipeline.py`

#### CI Pyflakes Step Added
- **ADDED**: Lint job with `pip install pyflakes` and `pyflakes geofactory/ tests/`
- **File**: `.github/workflows/ci.yml`

### Cinematic Scene Transitions (Previous Session)
- **ADDED**: Cinematic scene transitions using Visual Director's transition specifications
  - Implemented `_build_transition_filter()` helper generating FFmpeg xfade/fade filters
  - Supported transitions: `zoom_punch`, `wipe_map`, `dip_to_black`, `crossfade`, `cut`
  - Transition duration scales with segment length: max 1.5s, 15% of segment duration
  - Renderer reads `transition` field from ScenePlan (set by Visual Director per scene)
  - Evidence: `geofactory/media/documentary_renderer.py` lines 70-130
- **ADDED**: Transition filter unit tests (`tests/test_transitions.py`)
  - 8 tests covering all transition types: zoom_punch, wipe_map, dip_to_black, crossfade, cut, unknown
  - Tests verify filter structure, duration scaling, offset calculation
  - All tests PASS without requiring FFmpeg/PIL

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
- `tests/test_cli_smoke_regression.py` - CLI regression tests
- `tests/test_cli_shadow_audit.py` - AST-based shadow import audit
- `tests/test_smoke_runner.py` - Smoke runner logic tests

### New CLI Commands
- `plan-documentary JOB_ID --duration 600` - Creates documentary_plan.json, scene_manifest.json, asset_allocations.json
- `render-documentary JOB_ID --output final.mp4` - Renders from plan with per-scene asset mapping
- `shorts JOB_ID --duration 45 --hook "..."` - Generates YouTube Shorts (9:16 vertical)
- `produce JOB_ID --resume --duration 600 --shorts-duration 45` - Full automated pipeline
- `smoke --topic "Singapore" --seconds 60 --out output/smoke` - Full pipeline smoke test

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

