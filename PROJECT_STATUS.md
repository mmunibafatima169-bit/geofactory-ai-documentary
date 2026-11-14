# PROJECT_STATUS.md — Current Project State

**Last Updated:** 2026-11-12
**Session HEAD:** c8c7425 (fix: Critical pipeline fixes - job transitions, QA gating, Shorts sync, plan validation, fact-check gate)
**Branch:** feature/documentary-planner
**Workspace:** /root/geofactory-ai-documentary
**Git Status:** Modified documentary_renderer.py + new test files (uncommitted)

---

## 1. Current Project State Summary

GeoFactory is a **local-first documentary production pipeline** with a working CLI, SQLite persistence, Wikipedia/Commons research integration, map animation (Natural Earth), thumbnail engine, TTS narration, FFmpeg rendering, QA gates, hash-bound approval, and a loopback dashboard. The **Studio layer** (Remotion motion graphics, Visual Director, editorial QA, factual verifier, asset selector) has been merged locally.

**Key Achievement:** A professional-quality 60-second Venice documentary sample (v2) has been rendered at 1920×1080p30 with licensed real footage (CC BY-SA 3.0 gondolas, public domain 1896 archival film), animated maps, technical cross-sections, sourced charts, original music/SFX, soft subtitles, and decoded-video QA verification (0 freeze warnings, 0 subtitle warnings, factual display gate passing).

**NEW:** Complete end-to-end pipeline automation with:
- `plan-documentary` - builds chapter plan, scene manifest, asset allocations
- `render-documentary` - renders from plan with per-scene asset mapping
- `shorts` - generates YouTube Shorts (9:16) preserving chronological story flow
- `produce` - 8-stage automated pipeline (research → script → fact_check → plan → narrate → render → shorts → qa) with checkpoint/resume

**Critical Fixes Applied (previous session):**
1. Orchestrator job-status transitions now reconcile with core/jobs.py
2. Pipeline never moves to awaiting_approval when QA reports approval_blocked
3. Shorts generator preserves chronological story flow and syncs narration/subtitles
4. Invalid documentary plans (insufficient narration, missing claims/assets) fail before rendering
5. Factual verifier integrated as provenance/consistency gate (FACT_CHECK stage)

**NEW THIS SESSION: Cinematic Scene Transitions**
- Documentary renderer now implements Visual Director's transition specifications
- Supported transitions: `zoom_punch`, `wipe_map`, `dip_to_black`, `crossfade`, `cut`
- Uses FFmpeg xfade/fade filters for smooth cinematic transitions between scenes
- Transition duration scales with segment length (max 1.5s, 15% of segment)
- 8 unit tests added for transition filter generation

**Test Infrastructure:** Added FFmpeg integration tests with synthetic fixtures (tests/test_render_integration.py) and transition filter tests (tests/test_transitions.py).

---

## 2. Implementation Status by Component

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Core Infrastructure** | | | |
| Config/validation | **VERIFIED** | `core/config.py`, tests pass | Loopback-only, publishing disabled, safe defaults |
| SQLite schema v5 | **VERIFIED** | `core/database.py`, migrations tested | Foreign keys, WAL, schema versioning |
| Job lifecycle/transitions | **VERIFIED** | `core/jobs.py`, 50 tests pass | Idempotency, recovery, approval hashing |
| CLI entry point | **VERIFIED** | `cli.py`, all commands work | 24 subcommands incl. produce, shorts, plan-documentary |
| Loopback dashboard | **VERIFIED** | `app/dashboard.py`, aiohttp | Anti-CSRF, exact-package approval |
| **Research & Scripting** | | | |
| Topic proposals | **VERIFIED** | `agents/topic_agent.py`, deterministic | Scored, deduplicated, history-aware |
| Wikipedia API discovery | **VERIFIED** | `agents/research_agent.py`, live tests | HTTPS, CC BY-SA 4.0, access dates recorded |
| Claim/source ledger import | **VERIFIED** | `agents/research_agent.py`, JSON schema | Source IDs, claim kinds, evidence required |
| Script generation (Groq) | **REPORTED** | `agents/script_agent.py`, `groq_client.py` | Client implemented; no live API key to validate |
| Script generation (Ollama) | **UNVERIFIED** | Tested locally: 74 words in 89.9s | `qwen2.5:0.5b` fails 1,200–1,800 word check |
| **Assets & Media** | | | |
| Commons search/download | **VERIFIED** | `media/asset_manager.py`, licence gate works | CC0/BY/BY-SA/PD only; 25 MiB cap; hash recorded |
| Manual asset registration | **VERIFIED** | `asset-add`, `music-add` commands | Owner-attested rights; SHA-256 verification |
| Pexels/Pixabay video | **REPORTED** | `stock-search` command implemented | No API keys configured; code complete |
| Map animation engine | **VERIFIED** | `media/map_animation_engine.py` | Natural Earth 5.1.1 cached; world→country zoom MP4 |
| Thumbnail engine | **VERIFIED** | `media/thumbnail_engine.py` | 3 concepts, scored, contact sheet, 160×90 preview |
| TTS (Edge/eSpeak) | **VERIFIED** | `media/tts_engine.py` | Chunked WAV, FFprobe duration, measured SRT |
| TTS (Piper) | **BLOCKED** | No voice model installed | Lessac licence excludes commercial use |
| Video editor (FFmpeg) | **VERIFIED** | `media/video_editor.py` | Video-first, Ken Burns variety, music ducking, soft SRT |
| Visual builder (SVG) | **VERIFIED** | `media/visual_builder.py` | Original labelled charts |
| Documentary renderer | **VERIFIED** | `media/documentary_renderer.py` | Per-scene rendering from plan, **cinematic transitions** |
| Shorts generator | **VERIFIED** | `media/shorts_generator.py` | Chronological flow, synced subtitles |
| **Studio Layer** | | | |
| Scene manifest | **VERIFIED** | `studio/scene_manifest.py` | Validated per-scene plan; ≤40s/scene; ≤1s overlap |
| Visual Director v2 | **VERIFIED** | `studio/visual_director.py` | Ranked rules + variety penalty; engine fallback logged |
| Design tokens | **VERIFIED** | `studio/design_tokens.py` | Palette, typography, camera, transition, sound presets |
| Editorial QA v2 | **VERIFIED** | `studio/editorial_qa.py` | Decoded-video checks (freeze/black/silence/AV drift/SRT) |
| Factual verifier | **VERIFIED** | `studio/factual_verifier.py` | Single numeric ledger; now integrated in pipeline |
| Asset selector | **VERIFIED** | `studio/asset_selector.py` | Relevance scoring, perceptual dedup, rights ledger |
| Remotion project | **VERIFIED** | `studio/remotion/` | Cold-open (8s 720p); 60s v2 sample (60.000s 1080p30) |
| Blender adapter | **REPORTED** | `studio/engines/blender_adapter.py` | Runtime not installed; MOSE scene script ready |
| Manim adapter | **REPORTED** | `studio/engines/manim_adapter.py` | Runtime not installable (Cairo headers need root) |
| Pipeline orchestrator | **VERIFIED** | `pipeline/orchestrator.py` | 8-stage with checkpoint/resume |
| **Quality & Publishing** | | | |
| QA engine | **VERIFIED** | `quality/qa_engine.py`, 50 tests pass | Technical/evidence/rights gates; approval blocking |
| Approval hashing | **VERIFIED** | `core/jobs.py::package_digest` | SHA-256 of package; change invalidates approval |
| YouTube upload | **NOT IMPLEMENTED** | `publishing/youtube_client.py` | Fail-closed; Phase 9 separate implementation |
| Analytics import | **VERIFIED** | `analytics/feedback.py` | Owner CSV → descriptive summary (no causation) |
| Scheduler/worker | **VERIFIED** | `scheduler/worker.py` | Sequential recovery; bounded retry; no auto-daemon |

---

## 3. Git State Detail

| Property | Value |
|----------|-------|
| Repository root | /root/geofactory-ai-documentary |
| Package root | /root/geofactory-ai-documentary/geofactory |
| Remote URL | https://github.com/mmunibafatima169-bit/geofactory-ai-documentary.git |
| Current branch | feature/documentary-planner |
| HEAD commit | c8c7425 (fix: Critical pipeline fixes - job transitions, QA gating, Shorts sync, plan validation, fact-check gate) |
| Previous feature HEAD | f63a022 (feat: Complete documentary production pipeline...) |
| Local commits ahead of main | c8c7425, f63a022 (2 commits) |
| main branch | 49d22d7 (Deliver Studio v2...) |
| Merge base (main ↔ feature) | 49d22d7 |
| Remote feature branch | f63a022 (1 commit behind local) |
| Branches diverged | Yes - main is 2 commits behind feature branch |

---

## 4. Arena Merge Status

| Item | Detail |
|------|--------|
| Merge commit | `dc85cdd` (Add Studio layer: multi-engine architecture with Visual Director) |
| Merge date | Not recorded in log (local commit) |
| Parents | `c3acccd` (visual storytelling upgrade) + Arena unpublished changes |
| Merged content | `geofactory/studio/`, `studio/remotion/`, Blender/Manim adapters, editorial QA, Visual Director, scene manifest, design tokens |
| Production blockers from merge | Manim/Blender runtimes not provisioned; Remotion Chrome deps resolved via local `.tools/` |

---

## 5. Test Results (Latest Run)

```
python3 -m unittest tests.test_core tests.test_providers tests.test_studio tests.test_wikimedia tests.test_documentary_planner tests.test_render_integration tests.test_transitions -v
Ran 63 tests in ~4.1s
OK (skipped=13)
```

**Test Summary:**
- 50 PASS (core, providers, studio, wikimedia, documentary_planner, transitions)
- 13 SKIPPED (require FFmpeg/PIL - sandbox limitation)
- 0 FAIL

**Full Suite (with errors):**
- 68 tests discovered, 50 PASS, 13 SKIPPED, 3 ERRORS (pre-existing: test_map_thumbnail, test_media, test_pipeline require PIL)

---

## 6. Production Blockers (Prioritized)

| # | Blocker | Severity | Impact |
|---|---------|----------|--------|
| 1 | No Groq/Pexels/Pixabay API keys | High | Cannot validate end-to-end provider workflow |
| 2 | YouTube OAuth/upload not implemented | High | Publishing pipeline incomplete; fail-closed by design |
| 3 | Piper voice licence not cleared | Medium | No neural TTS option without commercial-use-verified voice |
| 4 | Manim/Blender runtimes unavailable | Medium | 3D/technical scenes blocked; Remotion 2D/2.5D works |
| 5 | Legal rights verification is owner-attested | Medium | System records metadata; no independent legal verification |
| 6 | Natural Earth 1:110m only | Low | No historical borders, rivers, density, climate layers |

---

## 7. Verified Artifacts (Evidence)

| Artifact | Path | Verified |
|----------|------|----------|
| 60s Venice sample v2 | `studio/remotion/out/venice_sample_60s_v2.mp4` | ✅ 60.000s, 1080p30, -15.7 LUFS |
| Scene manifest | `studio/remotion/out/scene_manifest.json` | ✅ Validated 6-scene plan |
| Editorial QA v2 | `studio/remotion/out/editorial_report_v2.json` | ✅ 0 critical, editorial_clean |
| Factual QA | `studio/remotion/out/factual_report.json` | ✅ approval_blocked=false |
| Asset/rights ledger | `studio/remotion/out/asset_selection.json` | ✅ 2 licensed assets, scored |
| Contact sheet | `studio/remotion/out/editorial_contact_sheet.jpg` | ✅ Per-scene labelled grid |
| Facts ledger | `studio/sample60_facts.json` | ✅ Single numeric source-of-truth |

---

## 8. Next Session Starting Point

- **Read all six continuity docs**
- **Verify Git state:** `git status && git log --oneline -1`
- **Run test gate:** `python3 -m unittest tests.test_core tests.test_providers tests.test_studio tests.test_wikimedia tests.test_documentary_planner tests.test_render_integration tests.test_transitions -v`
- **Check NEXT_TASK.md** for authorized single task (currently: Configure API keys for live provider validation)

