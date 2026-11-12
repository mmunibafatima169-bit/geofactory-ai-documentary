# NEXT_TASK.md — Single Highest-Priority Next Task

**Last Updated:** 2026-11-12
**Status:** IN PROGRESS - Engineering improvements to complete pipeline
**Branch:** feature/documentary-planner
**HEAD:** 49d22d7

---

## Completed This Session (Engineering)

| Task | Status | Evidence |
|------|--------|----------|
| Fixed Documentary Planner segment duration bug | ✅ | 13/13 planner tests pass; integration tests now pass |
| Added `plan-documentary` CLI command | ✅ | Creates documentary_plan.json, scene_manifest.json, asset_allocations.json |
| Built `documentary_renderer.py` (per-scene FFmpeg rendering) | ✅ | Uses scene manifest + asset allocations for precise rendering |
| Added `render-documentary` CLI command | ✅ | Validates plan exists, renders from plan, runs QA |
| Built `shorts_generator.py` (YouTube Shorts 9:16 vertical) | ✅ | Auto-selects best scenes, adds hook text, fast pacing |
| Added `shorts` CLI command | ✅ | 15-60s duration, custom hook, vertical output |
| Built `pipeline/orchestrator.py` (end-to-end automation) | ✅ | 7-stage pipeline with checkpoint/resume |
| Added `produce` CLI command | ✅ | One-command full pipeline with resume support |
| Removed 6 duplicate continuity docs | ✅ | Kept only repo-root copies |
| All existing tests pass | ✅ | 65 tests pass (23 skipped - missing PIL/FFmpeg) |

---

## Next Highest-Priority Engineering Task

### Task: Implement Automated Fact-Checking Against Claim Ledger

**Objective:** Integrate `factual_verifier.py` into the pipeline to automatically verify all narrated numbers against the claim/source ledger, blocking render if unverified claims remain.

**Reason:** Currently all claims require manual human verification. The factual_verifier exists but isn't connected to the production pipeline. This is the #1 production blocker for unattended automation.

**Steps:**
1. Add fact-check stage to pipeline orchestrator (between script and plan)
2. Connect `verify_fact_ledger()` to run on script narration + scene manifest display text
3. Make pipeline fail-fast on critical findings (unsourced numbers, conflicts)
4. Add `claims-review` CLI integration for human verification workflow
5. Update job status transitions to include `fact_checking` stage

**Acceptance Criteria:**
- `geofactory produce` runs fact verification automatically
- Critical findings (conflicts, unsourced display numbers) block pipeline
- Warnings (human verification needed) allow continuation but flag for review
- `geofactory claims-review JOB_ID` shows interactive verification UI
- Verified claims marked in database, reflected in pipeline state

**Dependencies:** `factual_verifier.py` already implemented and tested

**Blockers:** None

**Verification:** Run pipeline on test job with known conflicts, verify blocking works

---

## Other Identified Engineering Work (Backlog)

| Priority | Task | Reason |
|----------|------|--------|
| High | Implement claim verification UI in dashboard | Human-in-the-loop for factual accuracy |
| Medium | Add multi-language narration support | Expand audience beyond US English |
| Medium | Implement Remotion rendering path for 8-15 min | Currently only FFmpeg; Remotion for motion graphics |
| Low | Add historical map layers (borders, rivers, climate) | Requires independent sourced datasets |
| Low | YouTube OAuth/upload (Phase 9) | Separate security-reviewed phase |

---

## If Blocked on Current Task

Move to: **Implement claim verification UI in dashboard** (integrate with existing editorial QA contact sheet)
