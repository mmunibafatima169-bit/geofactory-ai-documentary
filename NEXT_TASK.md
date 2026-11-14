# NEXT_TASK.md — Single Highest-Priority Next Task

**Last Updated:** 2026-11-12
**Status:** COMPLETED - Cinematic scene transitions implemented
**Branch:** feature/documentary-planner
**HEAD:** c8c7425

---

## Completed This Session (Cinematic Scene Transitions)

| Task | Status | Evidence |
|------|--------|----------|
| **Implement cinematic scene transitions in documentary renderer** | ✅ | Added `_build_transition_filter()` function supporting zoom_punch, wipe_map, dip_to_black, crossfade, cut |
| **Transition duration scaling** | ✅ | Duration scales with segment length (max 1.5s, 15% of segment) |
| **Transition filter tests** | ✅ | 8 unit tests in `tests/test_transitions.py` — all PASS |
| **Integration with Visual Director** | ✅ | Renderer reads `transition` field from ScenePlan (set by Visual Director) |

---

## Test Results

| Test Suite | Result |
|------------|--------|
| Core (config, jobs, rights) | 8 PASS |
| Providers (Groq, Pexels, Pixabay, TTS) | 4 PASS, 2 SKIPPED |
| Studio (scene_manifest, visual_director, editorial_qa, factual_verifier, asset_selector) | 9 PASS |
| Wikimedia (Commons, Wikipedia) | 7 PASS |
| Documentary Planner | 13 PASS |
| Render Integration (synthetic fixtures) | 11 SKIPPED (need FFmpeg/PIL) |
| **Transition Filters (NEW)** | **8 PASS** |
| **Total** | **50 PASS, 13 SKIPPED** |

---

## Next Highest-Priority Engineering Task

### Task: Configure API Keys for Live Provider Validation

**Objective:** Add API keys for Groq, Pexels, and Pixabay to the ignored `config.json` to enable live end-to-end provider workflow validation.

**Reason:** All provider code is implemented but unvalidated. Cannot confirm end-to-end production quality without live API access.

**Steps:**
1. Obtain API keys for Groq (script generation), Pexels (stock video), Pixabay (stock video)
2. Add keys to `config.json` (which is gitignored)
3. Run live integration tests for each provider
4. Validate script generation quality with Groq
5. Validate stock video search/download with Pexels/Pixabay

**Acceptance Criteria:**
- `geofactory script JOB_ID` produces 1,200–1,800 word script with Groq
- `geofactory stock-search` returns licensed video clips from Pexels/Pixabay
- Downloaded clips pass licence gate and render correctly

**Dependencies:** External API keys (user must provide)

**Blockers:** User must provide API keys; cannot proceed without them

**Verification:** Run provider integration tests with live keys

---

## Other Identified Engineering Work (Backlog)

| Priority | Task | Reason |
|----------|------|--------|
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
| GEOFACTORY_MASTER_CONTEXT.md | Updated HEAD to c8c7425; added cinematic transitions to verified progress; updated test counts |
| PROJECT_STATUS.md | Updated HEAD, test results, added cinematic transitions to summary |
| CHANGELOG.md | Updated with cinematic transitions entry |
| AGENT_RESUME_PROMPT.md | Updated HEAD reference to c8c7425 |

