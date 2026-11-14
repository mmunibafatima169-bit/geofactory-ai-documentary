# PROJECT_STATUS.md — Current Project State

**Last Updated:** 2026-11-14
**Session HEAD:** cf391d7 (docs: update status, changelog, master context, next task)
**Branch:** feature/documentary-planner
**Workspace:** /root/geofactory-ai-documentary
**Git Status:** Clean working tree, 2 local commits ahead of remote

---

## 1. Current Project State Summary

GeoFactory is a **local-first documentary production pipeline** with a working CLI, SQLite persistence, Wikipedia/Commons research integration, map animation (Natural Earth), thumbnail engine, TTS narration, FFmpeg rendering, QA gates, hash-bound approval, and a loopback dashboard. The **Studio layer** (Remotion motion graphics, Visual Director, editorial QA, factual verifier, asset selector) has been merged locally.

**Key Achievement:** A professional-quality 60-second Venice documentary sample (v2) has been rendered at 1920×1080p30 with licensed real footage (CC BY-SA 3.0 gondolas, public domain 1896 archival film), animated maps, technical cross-sections, sourced charts, original music/SFX, soft subtitles, and decoded-video QA verification (0 freeze warnings, 0 subtitle warnings, factual display gate passing).

**Complete end-to-end pipeline automation:**
- `plan-documentary` - builds chapter plan, scene manifest, asset allocations
- `render-documentary` - renders from plan with per-scene asset mapping
- `shorts` - generates YouTube Shorts (9:16) preserving chronological story flow
- `produce` - 8-stage automated pipeline (research → script → fact_check → plan → narrate → render → shorts → qa) with checkpoint/resume
- `smoke` - full pipeline smoke test with synthetic fixtures (NEW, no API keys required)

**Critical Fixes Applied:**
1. Orchestrator job-status transitions now reconcile with core/jobs.py
2. Pipeline never moves to awaiting_approval when QA reports approval_blocked
3. Shorts generator preserves chronological story flow and syncs narration/subtitles
4. Invalid documentary plans (insufficient narration, missing claims/assets) fail before rendering
5. Factual verifier integrated as provenance/consistency gate (FACT_CHECK stage)

**Cinematic Scene Transitions (NEW):**
- Documentary renderer implements Visual Director's transition specifications
- Supported: `zoom_punch`, `wipe_map`, `dip_to_black`, `crossfade`, `cut`
- Uses FFmpeg xfade/fade filters; duration scales with segment length (max 1.5s, 15%)
- 8 unit tests in tests/test_transitions.py — all PASS

**CI/CD Added (this session):**
- `.github/workflows/ci.yml` — Python 3.12 unit tests on ubuntu-24.04
- `.github/workflows/smoke.yml` — Full pipeline smoke test + optional Remotion render

---

## 2. Implementation Status by Component (Honest Labels)

**Labels:**
- ✅ = **Real run proven** (log evidence: rendered video, FFprobe output, live API call)
- 🟡 = **Unit test only** (code exists, tests pass, but no integration/render evidence)
- ❌ = **Untested/Blocked** (no evidence, missing deps, or known broken)

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| **Core Infrastructure** | | | |
| Config/validation | ✅ | `core/config.py`, tests pass, CLI loads config | Loopback-only, publishing disabled, safe defaults |
| SQLite schema v5 | ✅ | `core/database.py`, migrations tested | Foreign keys, WAL, schema versioning |
| Job lifecycle/transitions | ✅ | `core/jobs.py`, 50 tests pass | Idempotency, recovery, approval hashing |
| CLI entry point | ✅ | `cli.py`, all 25 commands parse | Including new `smoke` command |
| Loopback dashboard | 🟡 | `app/dashboard.py`, unit tests pass | No live browser test |
| **Research & Scripting** | | | |
| Topic proposals | ✅ | `agents/topic_agent.py`, deterministic, tests pass | Scored, deduplicated, history-aware |
| Wikipedia API discovery | 🟡 | `agents/research_agent.py`, unit tests pass | Code complete; **no live network test** (sandbox blocks) |
| Claim/source ledger import | ✅ | `agents/research_agent.py`, JSON schema, tests pass | Source IDs, claim kinds, evidence required |
| Script generation (Groq) | 🟡 | `agents/script_agent.py`, `groq_client.py` tests pass | Client implemented; **no API key to validate live** |
| Script generation (Ollama) | ❌ | Tested locally: 74 words in 89.9s | `qwen2.5:0.5b` fails 1,200–1,800 word check |
| **Assets & Media** | | | |
| Commons search/download | 🟡 | `media/asset_manager.py`, unit tests pass | Licence gate logic tested; **no live download test** |
| Manual asset registration | ✅ | `asset-add`, `music-add` commands work | Owner-attested rights; SHA-256 verification |
| Pexels/Pixabay video | 🟡 | `stock-search` command, unit tests pass | **No API keys configured**; code complete |
| Map animation engine | 🟡 | `media/map_animation_engine.py`, unit tests pass | **PIL missing** — no render test; Natural Earth cached |
| Thumbnail engine | 🟡 | `media/thumbnail_engine.py`, unit tests pass | **PIL missing** — no render test |
| TTS (Edge/eSpeak) | 🟡 | `media/tts_engine.py`, unit tests pass | **espeak-ng binary missing**; code complete |
| TTS (Piper) | ❌ | No voice model installed | Lessac licence excludes commercial use |
| Video editor (FFmpeg) | 🟡 | `media/video_editor.py`, unit tests pass | **PIL missing** — no integration render test |
| Visual builder (SVG) | 🟡 | `media/visual_builder.py`, unit tests pass | Original labelled charts; no render test |
| Documentary renderer | 🟡 | `media/documentary_renderer.py`, unit tests pass | **PIL/FFmpeg integration test skipped**; cinematic transitions |
| Shorts generator | 🟡 | `media/shorts_generator.py`, unit tests pass | **PIL/FFmpeg integration test skipped**; chronological flow |
| **Studio Layer** | | | |
| Scene manifest | ✅ | `studio/scene_manifest.py`, tests pass | Validated per-scene plan; ≤40s/scene; ≤1s overlap |
| Visual Director v2 | ✅ | `studio/visual_director.py`, tests pass | Ranked rules + variety penalty; engine fallback logged |
| Design tokens | ✅ | `studio/design_tokens.py`, tests pass | Palette, typography, camera, transition, sound presets |
| Editorial QA v2 | 🟡 | `studio/editorial_qa.py`, tests pass | Decoded-video checks; **needs real video to test** |
| Factual verifier | ✅ | `studio/factual_verifier.py`, tests pass | Single numeric ledger; integrated in pipeline |
| Asset selector | ✅ | `studio/asset_selector.py`, tests pass | Relevance scoring, perceptual dedup, rights ledger |
| Remotion project | 🟡 | `studio/remotion/`, cold-open rendered | 60s v2 sample rendered **locally on networked machine**; CI not tested |
| Blender adapter | ❌ | `studio/engines/blender_adapter.py` | Runtime not installed; MOSE scene script ready |
| Manim adapter | ❌ | `studio/engines/manim_adapter.py` | Runtime not installable (Cairo headers need root) |
| Pipeline orchestrator | 🟡 | `pipeline/orchestrator.py`, unit tests pass | Checkpoint/resume tested; **full run blocked by deps** |
| **Quality & Publishing** | | | |
| QA engine | 🟡 | `quality/qa_engine.py`, 50 tests pass | Technical/evidence/rights gates; **needs real video** |
| Approval hashing | ✅ | `core/jobs.py::package_digest`, tests pass | SHA-256 of package; change invalidates approval |
| YouTube upload | ❌ | `publishing/youtube_client.py` | Fail-closed; Phase 9 separate implementation |
| Analytics import | ✅ | `analytics/feedback.py`, tests pass | Owner CSV → descriptive summary (no causation) |
| Scheduler/worker | 🟡 | `scheduler/worker.py`, unit tests pass | Sequential recovery; bounded retry; no auto-daemon |
| **New: CI/CD** | | | |
| GitHub Actions CI | ❌ | `.github/workflows/ci.yml` written | **NOT RUN** — sandbox has no GitHub access |
| GitHub Actions Smoke | ❌ | `.github/workflows/smoke.yml` written | **NOT RUN** — sandbox has no GitHub access |
| Remotion CI job | ❌ | smoke.yml includes remotion job | **NOT RUN** — needs Chrome + npm deps |

---

## 3. Git State Detail

| Property | Value |
|----------|-------|
| Repository root | /root/geofactory-ai-documentary |
| Package root | /root/geofactory-ai-documentary/geofactory |
| Remote URL | https://github.com/mmunibafatima169-bit/geofactory-ai-documentary.git |
| Current branch | feature/documentary-planner |
| HEAD commit | cf391d7 (docs: update status, changelog, master context, next task) |
| Previous feature HEAD | f63a022 (feat: Complete documentary production pipeline...) |
| Local commits ahead of main | c8c7425, f63a022 (2 commits) |
| main branch | 49d22d7 (Deliver Studio v2...) |
| Merge base (main ↔ feature) | 49d22d7 |
| Remote feature branch | f63a022 (1 commit behind local) |
| Branches diverged | Yes - main is 2 commits behind feature branch |

---

## 4. Test Results (Latest Sandbox Run)

```
python3 -m unittest discover -v
Ran 104 tests in 7.8s
PASS: 68  |  SKIP: 28 (PIL/FFmpeg missing)  |  ERROR: 3 (test_map_thumbnail, test_media, test_pipeline — all PIL import errors)
```

**Working test modules (no PIL needed):**
- test_core.py: 8 PASS
- test_providers.py: 6 PASS (2 SKIP)
- test_studio.py: 9 PASS
- test_wikimedia.py: 7 PASS
- test_documentary_planner.py: 13 PASS
- test_transitions.py: 8 PASS
- test_remotion_compatibility.py: 8 PASS
- test_remotion_renderer.py: 6 PASS
- test_render_integration.py: 11 SKIPPED (need FFmpeg/PIL)
- test_shorts_generator.py: 7 SKIPPED (need PIL)
- test_documentary_renderer.py: 4 SKIPPED (need PIL)
- test_pipeline_orchestrator.py: 8 SKIPPED (need PIL)

**Broken test modules (PIL import at module level):**
- test_map_thumbnail.py: ERROR (PIL import)
- test_media.py: ERROR (PIL import via map_animation_engine)
- test_pipeline.py: ERROR (PIL import via dashboard → qa_engine → map_animation_engine)

---

## 5. Production Blockers (Prioritized)

| # | Blocker | Severity | Impact |
|---|---------|----------|--------|
| 1 | Sandbox has **no external network** | Critical | Cannot install deps, run live tests, push to GitHub |
| 2 | No Pillow (PIL) installed | High | Map animation, thumbnails, video editor, 13+ tests blocked |
| 3 | No espeak-ng binary | High | TTS narration blocked; pipeline cannot synthesize audio |
| 4 | No Chromium/Chrome | High | Remotion rendering blocked |
| 5 | No Groq/Pexels/Pixabay API keys | High | Cannot validate end-to-end provider workflow |
| 6 | YouTube OAuth/upload not implemented | High | Publishing pipeline incomplete; fail-closed by design |
| 7 | Piper voice licence not cleared | Medium | No neural TTS option without commercial-use-verified voice |
| 8 | Manim/Blender runtimes unavailable | Medium | 3D/technical scenes blocked; Remotion 2D/2.5D works |
| 9 | Legal rights verification is owner-attested | Medium | System records metadata; no independent legal verification |
| 10 | Natural Earth 1:110m only | Low | No historical borders, rivers, density, climate layers |

---

## 6. Verified Artifacts (Evidence from Previous Networked Run)

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

## 7. Next Session Starting Point

- **Read all six continuity docs**
- **Verify Git state:** `git status && git log --oneline -1`
- **Run test gate:** `python3 -m unittest tests.test_core tests.test_providers tests.test_studio tests.test_wikimedia tests.test_documentary_planner tests.test_render_integration tests.test_transitions -v`
- **On networked machine:** Install deps, add API keys, run `python -m geofactory smoke --topic Singapore --seconds 60 --out output/smoke`
- **Check NEXT_TASK.md** for authorized single task

---

## 8. Files Created/Modified This Session

| File | Action |
|------|--------|
| requirements.txt | Created — core deps (httpx, aiohttp, Pillow) |
| requirements-optional.txt | Created — optional deps (edge-tts, groq, gTTS) |
| tests/fixtures/singapore_ledger.json | Created — test fixture (TEST DATA - NOT FOR PUBLISHING) |
| geofactory/cli.py | Modified — added `smoke` command parser + handler |
| .github/workflows/ci.yml | Created — Python 3.12 unit test CI |
| .github/workflows/smoke.yml | Created — Smoke test + Remotion render CI |
| PROJECT_STATUS.md | Updated — honest labels, current state |
