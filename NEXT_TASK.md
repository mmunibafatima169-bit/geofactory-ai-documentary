# NEXT_TASK.md — Single Highest-Priority Next Task

**Last Updated:** 2026-11-15
**Status:** COMPLETED - All critical fixes applied, CI/CD updated, test suite passing
**Branch:** feature/documentary-planner
**HEAD:** 90cad1d

---

## Completed This Session (Critical Fixes & CI/CD)

| Task | Status | Evidence |
|------|--------|----------|
| **Fix CLI shadowed imports (BUG 1)** | ✅ | Removed local `from pathlib import Path` from `run()`; extracted `_cmd_smoke()` with lazy imports |
| **Add smoke profile for plan validation (BUG 2)** | ✅ | Added `profile` param to `validate_documentary_plan()` and `run_documentary_plan()` |
| **Fix CI pipefail (BUG 3)** | ✅ | Added `shell: bash` + `set -o pipefail`; proper exit code capture in smoke.yml |
| **Fix Shorts FFmpeg filtergraph (BUG 1 - new)** | ✅ | Moved scale/crop/setsar into filter_complex with `[vfinal]` label |
| **Fix checkpoint directory (BUG 2 - new)** | ✅ | Added `mkdir(parents=True, exist_ok=True)` in `save_pipeline_state()` |
| **Fix orchestrator tests (BUG 3 - new)** | ✅ | Restored `test_run_full_pipeline_research_only` with proper mocking |
| **Fix error-message drift (BUG 4 - new)** | ✅ | Exception type + key substring checks instead of exact strings |
| **Fix licence fixture (BUG 5 - new)** | ✅ | Changed "Test License" to "CC0-1.0" |
| **Fix scene priority test (BUG 6 - new)** | ✅ | Updated to match actual algorithm (contiguous chronological window) |
| **Add profile test (BUG 7 - new)** | ✅ | Permanent test: production rejects 88-word, smoke accepts |
| **Make thumbnail_engine lazy-PIL (A1)** | ✅ | Added `_lazy_pil()` helper; all 6 functions import lazily |
| **Fix smoke ledger path & import (A2)** | ✅ | Repo-relative path; `import_ledger_data()` for dict |
| **Fix CLI smoke regression test env (A3)** | ✅ | Added `PYTHONPATH` to subprocess env |
| **Create shadow audit test** | ✅ | AST-based test enforcing no shadowed imports in `run()` |
| **Fix pipeline test PIL check** | ✅ | Runtime `PIL_AVAILABLE` check replacing broken import-time check |
| **Add CI pyflakes step** | ✅ | Lint job with `pip install pyflakes` and `pyflakes geofactory/ tests/` |

---

## Test Results

| Test Suite | Pass | Fail | Error | Skip |
|------------|------|------|-------|------|
| test_core | 8 | 0 | 0 | 0 |
| test_providers | 5 | 0 | 0 | 0 |
| test_studio | 11 | 0 | 0 | 0 |
| test_wikimedia | 7 | 0 | 0 | 0 |
| test_documentary_planner | 13 | 0 | 0 | 0 |
| test_transitions | 8 | 0 | 0 | 0 |
| test_cli_smoke_regression | 3 | 0 | 0 | 0 |
| test_cli_shadow_audit | 3 | 0 | 0 | 0 |
| test_smoke_runner | 4 | 0 | 0 | 0 |
| test_shorts_generator | 8 | 0 | 0 | 0 |
| test_documentary_renderer | 6 | 0 | 0 | 0 |
| test_pipeline_orchestrator | 8 | 0 | 0 | 0 |
| test_render_integration | 4 | 0 | 0 | 7 |
| test_pipeline | 2 | 0 | 0 | 6 |
| test_map_thumbnail | 0 | 0 | 0 | 5 |
| test_media | 2 | 0 | 0 | 4 |
| **Total** | **92** | **0** | **0** | **22** |

---

## Next Highest-Priority Engineering Task

### Task: Map Animation Engine Lazy-PIL (A1 Completion)

**Objective:** Make `map_animation_engine.py` fully lazy-PIL-safe (check `_draw_arrow` uses `ImageDraw` in type hint; move all PIL usage inside functions).

**Reason:** CI pyflakes check will catch undefined names at module level. The map animation engine currently has PIL imports at module level in some functions and type hints referencing PIL types.

**Steps:**
1. Inspect `geofactory/media/map_animation_engine.py` for all PIL usage
2. Add `_lazy_pil()` helper similar to `thumbnail_engine.py`
3. Move all PIL imports inside functions that use them
4. Fix type hints to use string annotations (e.g., `"Image.Image"` instead of `Image.Image`)
5. Verify with `python -m pyflakes geofactory/media/map_animation_engine.py` (when pyflakes available)
6. Run unit tests to ensure nothing breaks

**Acceptance Criteria:**
- `pyflakes geofactory/media/map_animation_engine.py` shows no "undefined name" errors
- Module loads without PIL installed
- All existing unit tests still pass

**Dependencies:** None (can be done in sandbox)

**Blockers:** None

**Verification:** Run test suite, check pyflakes output

---

## Other Identified Engineering Work (Backlog)

| Priority | Task | Reason |
|----------|------|--------|
| High | Complete A1: map_animation_engine.py lazy-PIL | CI pyflakes will catch module-level PIL refs |
| High | Resolve Piper voice licence or confirm eSpeak NG fallback | No neural TTS option |
| Medium | Implement Remotion rendering path for 8-15 min | Currently only FFmpeg |
| Medium | Enhanced thumbnail engine with licensed cut-out photos | RealLifeLore-style thumbnails need photo elements |
| Medium | Timeline editor for map-scene synchronization | Schedule maps/overlays against narration claims |
| Low | Add historical map layers | Requires independent datasets |
| Low | YouTube OAuth/upload (Phase 9) | Separate security-reviewed phase |

---

## Continuity Document Corrections Applied

| Document | Corrections Applied |
|----------|---------------------|
| PROJECT_STATUS.md | Updated HEAD to 90cad1d; added all critical fixes; updated test counts (92 pass, 22 skip); updated git state |
| CHANGELOG.md | Updated with all critical fixes and CI/CD entries |
| AGENT_RESUME_PROMPT.md | (to be updated) |

