# NEXT_TASK.md — Single Highest-Priority Next Task

**Last Updated:** 2026-11-12
**Status:** IN PROGRESS - Critical fixes to pipeline
**Branch:** feature/documentary-planner
**HEAD:** f63a022

---

## Completed This Session (Critical Fixes)

| Task | Status | Evidence |
|------|--------|----------|
| **Fix 1: Reconcile orchestrator job-status transitions** | ✅ | Orchestrator now uses valid transitions from core/jobs.py STATUSES/TRANSITIONS; added `_transition_job_safely()` helper |
| **Fix 2: Never move to awaiting_approval when QA blocks** | ✅ | Pipeline now checks `qa_report["approval_blocked"]` and transitions to `qa_failed` if blocked |
| **Fix 3: Fix Shorts chronological flow & sync** | ✅ | Shorts generator now selects scenes in chronological order, maps SRT segments to shorts timeline, validates output duration |
| **Fix 4: Invalid plans fail before rendering** | ✅ | Added `InvalidPlanError`, strict validation in `run_plan_stage` raises on critical structure errors |
| **Fix 5: Integrate factual_verifier as gate** | ✅ | Added `FACT_CHECK` stage between script and plan; runs `verify_fact_ledger()`; blocks on critical findings |

---

## Test Results

| Test Suite | Result |
|------------|--------|
| Core (config, jobs, rights) | 8 PASS |
| Providers (Groq, Pexels, Pixabay, TTS) | 4 PASS, 2 SKIPPED |
| Studio (scene_manifest, visual_director, editorial_qa, factual_verifier, asset_selector) | 9 PASS |
| Wikimedia (Commons, Wikipedia) | 7 PASS |
| Documentary Planner | 13 PASS |
| **Total** | **44 PASS, 2 SKIPPED** |

---

## Next Highest-Priority Engineering Task

### Task: Add FFmpeg Integration Tests with Synthetic Fixtures

**Objective:** Create focused FFmpeg integration tests using tiny synthetic fixtures (not demo videos) to verify rendering pipeline end-to-end.

**Reason:** Current tests skip FFmpeg-dependent modules due to missing tools in sandbox. Need lightweight synthetic tests that can run in CI to catch regressions in rendering logic.

**Steps:**
1. Create synthetic MP4/WAV fixtures using FFmpeg `lavfi` (testsrc, sine)
2. Add tests for `video_editor.py`, `documentary_renderer.py`, `shorts_generator.py` using synthetic fixtures
3. Verify actual output duration matches plan
4. Test error handling for missing assets, invalid plans, etc.

**Acceptance Criteria:**
- Tests run without downloading external assets
- Tests verify output file exists, has correct duration, valid container
- Tests added to `tests/test_media.py` and new `tests/test_render_integration.py`

**Dependencies:** FFmpeg/FFprobe available (already in sandbox)

**Blockers:** None

**Verification:** `python3 -m unittest tests.test_render_integration -v`

---

## Other Identified Engineering Work (Backlog)

| Priority | Task | Reason |
|----------|------|--------|
| High | Configure API keys for live provider validation | Groq/Pexels/Pixabay unvalidated |
| Medium | Resolve Piper voice licence or confirm eSpeak NG fallback | No neural TTS option |
| Medium | Implement Remotion rendering path for 8-15 min | Currently only FFmpeg |
| Low | Add historical map layers | Requires independent datasets |
| Low | YouTube OAuth/upload (Phase 9) | Separate security-reviewed phase |
