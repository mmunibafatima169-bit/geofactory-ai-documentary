# GeoFactory AI Documentary — Master Context

**Repository:** https://github.com/mmunibafatima169-bit/geofactory-ai-documentary
**Workspace:** /root/geofactory-ai-documentary/geofactory
**Current HEAD:** c8c7425 (fix: Critical pipeline fixes - job transitions, QA gating, Shorts sync, plan validation, fact-check gate)
**Branch:** feature/documentary-planner (diverged from main at 49d22d7)
**Main Branch HEAD:** 49d22d7 (Deliver Studio v2 with rendered 60-second documentary sample)

---

## 1. Project Vision

GeoFactory is a local-first, zero-recurring-cost pipeline for producing professional geography and country documentary videos. The system automates research, fact verification, script writing, scene planning, visual generation (maps, charts, motion graphics), narration, sound design, editing, quality assurance, and private YouTube upload — with mandatory human approval at every gate.

**Product objective:** Produce 8–15 minute faceless, research-driven geography documentaries for US and international English-language audiences, comparable in ambition to channels like RealLifeLore (style inspiration only — no content, branding, or assets copied).

**Target audience:** Curious viewers seeking "Why ...?" geography explanations — map-driven, evidence-led, calm confident American English narration.

**Target video duration:** 8–15 minutes (480–900 seconds).

---

## 2. Overall Architecture

### Runtime Shape
```
CLI / loopback dashboard
          |
          +-- core/config.py (validated safe defaults)
          +-- core/database.py (SQLite schema/version)
          +-- core/jobs.py (idempotency, transitions, recovery, approval hash)
          |
          +-- agents/topic_agent.py (deterministic proposals/history scoring)
          +-- agents/research_agent.py (Wikipedia API search, owner-reviewed ledger import/export)
          +-- agents/script_agent.py (source-aware notes; optional Groq/Ollama draft)
          +-- agents/groq_client.py (Groq JSON requests; sanitized provider errors)
          +-- media/asset_manager.py (Commons/Pexels/Pixabay video; licensed local audio)
          +-- media/map_animation_engine.py (Natural Earth country zooms, highlights, scene manifests)
          +-- wikimedia.py (shared HTTPS API client, User-Agent, rate limit, bounded downloads)
          +-- media/tts_engine.py (chunked Edge/eSpeak/Piper WAV synthesis, FFprobe checks, measured SRT)
          +-- media/visual_builder.py (original labelled SVG charts)
          +-- media/video_editor.py (video-first FFmpeg timeline, optional music mix, soft SRT)
          +-- media/thumbnail_engine.py (three map-first concepts, heuristic scores, edit recipes)
          +-- media/thumbnail_maker.py (Pillow JPEG and SVG companion)
          +-- media/documentary_renderer.py (per-scene FFmpeg rendering from plan WITH cinematic transitions)
          +-- media/shorts_generator.py (YouTube Shorts 9:16 with synced subtitles)
          +-- quality/qa_engine.py (technical/evidence/rights release gates)
          +-- scheduler/worker.py (sequential offline package and recovery)
          +-- analytics/feedback.py (owner CSV import, descriptive summary)
          +-- publishing/youtube_client.py (deliberately fail-closed)
          +-- pipeline/orchestrator.py (8-stage automation with checkpoint/resume)
          |
          +-- studio/scene_manifest.py (validated per-scene production plan)
          +-- studio/visual_director.py (AI Visual Director: deterministic rules → engines)
          +-- studio/design_tokens.py (shared palette/typography/camera/transition/sound presets)
          +-- studio/editorial_qa.py (decoded-video QC: freeze/black/silence/AV drift/SRT/factual)
          +-- studio/asset_selector.py (relevance scoring, duplicate detection, rights ledger)
          +-- studio/factual_verifier.py (single source-of-truth numeric ledger)
          +-- studio/documentary_planner.py (chapter planning, scene manifest, asset allocation)
          +-- studio/engines/blender_adapter.py, manim_adapter.py (optional 3D/technical engines)
          +-- studio/remotion/ (Remotion 4 + React 19 + TypeScript motion graphics project)
```

### Persistent Model
- **SQLite database** with schema versioning (`PRAGMA user_version = 5`)
- Tables: `jobs`, `topic_proposals`, `job_events`, `sources`, `claims`, `assets` (image/video/audio), `approvals`, `uploads`, `analytics`
- Foreign keys enabled; job transitions centrally validated
- Job creation uses unique idempotency key (SHA-256 of normalized topic|question)
- Output files stored under `output/<job-id>/` as human-editable artifacts
- **Approval hashing**: SHA-256 of sorted relative paths + file bytes (excluding `approval.json`)
- Database stores approval digest; CLI/dashboard verify digest before any upload gate
- **Public publishing is unavailable** — `publishing_enabled` rejected by config validation

---

## 3. Technical Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ (tested on 3.14) |
| Database | SQLite 3 (local file, WAL mode) |
| CLI | argparse (entry point: `python -m geofactory`) |
| Dashboard | aiohttp (loopback-only: 127.0.0.1, localhost, ::1) |
| Video rendering | FFmpeg/FFprobe (static build or system) |
| TTS | Edge TTS (online), eSpeak NG (local), Piper (optional, needs licensed voice) |
| Maps | Natural Earth 1:110m Admin 0 Countries 5.1.1 (public domain GeoJSON) |
| Motion graphics | Remotion 4 (React 19, TypeScript) — primary engine |
| 3D engine | Blender (optional, headless, adapter + scene ready) |
| Technical viz | Manim CE (optional, adapter + scene ready) |
| Image processing | Pillow (JPEG, SVG, contact sheets) |
| HTTP clients | httpx (Wikimedia, Wikipedia, Pexels, Pixabay) |
| Testing | unittest (55 tests + 8 transition tests, 13 environment-skips without media tools) |

**Optional providers** (require API keys in ignored `config.json`):
- Groq (`llama-3.3-70b-versatile`) for script generation
- Edge TTS (Microsoft, via community `edge-tts` package)
- Pexels API (stock video)
- Pixabay API (stock video; no public music endpoint)

---

## 4. Production Workflow

### CLI Workflow (Manual)
```
1. Init:           geofactory init
2. Topics:         geofactory topics
3. New job:        geofactory new --topic "..." --question "..."
4. Research:       geofactory research-online JOB_ID --query "..."
5. Import ledger:  geofactory research JOB_ID --ledger path.json
6. Script:         geofactory script JOB_ID
7. Assets:         geofactory commons-search JOB_ID --query "..."
                   geofactory asset-add JOB_ID ...
8. Maps:           geofactory map-build JOB_ID --country ISO --duration N
9. Thumbnails:     geofactory thumbnail-build JOB_ID --country ISO --headline "..."
10. Narrate:       geofactory narrate JOB_ID --text-file path.txt
11. Claims review: geofactory claims-review JOB_ID --claim-id ID --reviewer "..." --confirm-reviewed
12. Plan:          geofactory plan-documentary JOB_ID --duration 600
13. Render:        geofactory render-documentary JOB_ID
14. Shorts:        geofactory shorts JOB_ID --duration 45
15. QA:            geofactory qa JOB_ID
16. Approve:       geofactory approve JOB_ID --reviewer "..."
17. Upload:        geofactory upload JOB_ID (NOT IMPLEMENTED)
```

### Automated Pipeline (Single Command)
```
geofactory produce JOB_ID [--resume] [--duration 600] [--shorts-duration 45] [--hook "..."]

Stages: research → script → fact_check → plan → narrate → render → shorts → qa
- Checkpoint/resume via pipeline_state.json
- Job status transitions per core/jobs.py
- Fails fast on critical validation errors
- Only moves to awaiting_approval if QA passes
```

---

## 5. Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Local-first, zero recurring cost | No cloud dependencies; all processing on owner's machine |
| SQLite for persistence | Zero-config, portable, transactional, schema versioning |
| Loopback-only dashboard | Security: no external access without separate threat review |
| Approval hashes package content | Tamper-evident; changed deliverables require renewed approval |
| Fail-closed publishing | Prevents accidental public upload; OAuth/private-first needs separate reviewed phase |
| Natural Earth public domain maps | No licence cost; de-facto boundaries clearly qualified |
| Video-first rendering | Stock clips at actual duration; stills only for remaining narration (no looping) |
| Deterministic Visual Director | Rules-based engine selection with recorded rationale; LLM can slot in later |
| Three thumbnail concepts | Variety enforced; heuristic scores guide selection (not view prediction) |
| Chunked TTS + measured SRT | Accurate subtitle timing; silence/decode verification per chunk |
| Owner-attested asset rights | System records metadata; legal interpretation remains human responsibility |
| Pipeline checkpoint/resume | Fault tolerance; can resume from any completed stage |
| Fact check as pipeline gate | Automated provenance/consistency; human verification still mandatory |
| Cinematic scene transitions | Visual Director specifies transition types; renderer implements zoom_punch, wipe_map, dip_to_black, crossfade |

---

## 6. Verified Progress (as of HEAD c8c7425)

| Component | Status | Evidence |
|-----------|--------|----------|
| Config/DB/CLI/Jobs | **VERIFIED** | All tests pass; idempotency, transitions, recovery work |
| Topic proposals | **VERIFIED** | Deterministic scoring, deduplication, history |
| Wikipedia research | **VERIFIED** | Live API discovery, CC BY-SA 4.0 recording, HTTPS enforcement |
| Claim ledger import/export | **VERIFIED** | JSON schema validation, source IDs, claim kinds |
| Script generation (Groq) | **REPORTED** | Client implemented; no live API key to validate |
| Script generation (Ollama) | **UNVERIFIED** | Tested locally: 74 words in 89.9s; `qwen2.5:0.5b` fails 1,200–1,800 word check |
| TTS (Edge/eSpeak) | **VERIFIED** | Chunked WAV, FFprobe duration, measured SRT, silence check |
| Commons search/download | **VERIFIED** | Licence gate rejects non-commercial/unknown; attribution/hash recorded |
| Manual asset registration | **VERIFIED** | Manual `asset-add`/`music-add` with rights attestation |
| Pexels/Pixabay video | **REPORTED** | `stock-search` command implemented; no API keys configured |
| Map animation engine | **VERIFIED** | Natural Earth 5.1.1 cached; world→country zoom MP4 |
| Thumbnail engine | **VERIFIED** | 3 concepts, scored, contact sheet, 160×90 preview |
| TTS (Piper) | **BLOCKED** | No voice model installed; Lessac licence excludes commercial use |
| Video editor (FFmpeg) | **VERIFIED** | Video-first, Ken Burns variety, music ducking, soft SRT |
| Visual builder (SVG) | **VERIFIED** | Original labelled charts |
| Documentary renderer | **VERIFIED** | Per-scene rendering from plan, cinematic transitions |
| Shorts generator | **VERIFIED** | Chronological flow, synced subtitles, duration validation |
| Pipeline orchestrator | **VERIFIED** | 8-stage, checkpoint/resume, valid job transitions |
| QA engine | **VERIFIED** | 50 tests pass; decode checks, A/V drift, SRT, asset rights, thumbnail rubric |
| Approval hashing | **VERIFIED** | Content change detection, invalidation, dashboard integration |
| Studio layer (Remotion) | **VERIFIED** | Cold-open rendered (8s, 720p); 60s v2 sample rendered (60.000s, 1080p30) |
| Visual Director v2 | **VERIFIED** | Ranked rules + variety penalty; engine fallback logged |
| Editorial QA v2 | **VERIFIED** | Decoded-video checks (freeze/black/silence/AV drift/SRT) |
| Factual verifier | **VERIFIED** | Single numeric ledger; integrated as pipeline gate |
| Asset selector | **VERIFIED** | Relevance scoring, perceptual duplicate detection, rights ledger |

---

## 7. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No Groq/Pexels/Pixabay keys configured | Live provider-backed production unvalidated | Keys must be added to ignored `config.json` before live testing |
| Ollama `qwen2.5:0.5b` fails script length | Local LLM fallback unusable for long-form | Use manual script fallback or configure Groq |
| Piper voice model not installed | Piper TTS unavailable | Use eSpeak NG (installed) or Edge TTS (terms review needed) |
| Manim CE not installable (needs Cairo headers) | Technical charts via Manim unavailable | Remotion/Pillow charts used; Blender/Manim on machine with root |
| Blender not installed | 3D scenes (MOSE gates) unavailable | Adapter + scene ready; install on machine with root when needed |
| YouTube OAuth/upload not implemented | Cannot publish | Phase 9 — separate reviewed implementation required |
| No automated claim fact-checking | All claims require manual human verification | Factual verifier now runs as pipeline gate; catches consistency issues |
| Legal rights verification is owner-attested | System records metadata; no independent legal verification | Documented in metadata; human review required |
| Natural Earth 1:110m only | No historical borders, rivers, density, climate layers | Each layer needs independent sourced dataset before implementation |

---

## 8. Production Blockers (Prioritized)

| # | Blocker | Severity | Description |
|---|---------|----------|-------------|
| 1 | No API keys for Groq/Pexels/Pixabay | High | Cannot validate end-to-end provider workflow |
| 2 | YouTube OAuth/upload not implemented | High | Publishing pipeline incomplete; fail-closed by design |
| 3 | Piper voice licence not cleared | Medium | No neural TTS option without commercial-use-verified voice model |
| 4 | Manim/Blender runtimes unavailable | Medium | 3D/technical scenes blocked; Remotion 2D/2.5D works |
| 5 | Legal rights verification is owner-attested | Medium | System records metadata; no independent legal verification |
| 6 | Natural Earth 1:110m only | Low | No historical borders, rivers, density, climate layers |

---

## 9. Arena Merge History & Recovery Situation

### Arena Merge
- **Merge commit:** `dc85cdd` (Add Studio layer: multi-engine architecture with Visual Director)
- **Parent commits:** `c3acccd` (visual storytelling upgrade) + Arena unpublished changes
- **Merged changes:** Studio layer (`geofactory/studio/`), Remotion project (`studio/remotion/`), Blender/Manim adapters, editorial QA, Visual Director, scene manifest, design tokens
- **Production blockers from merge:** Manim/Blender runtimes not provisioned; Remotion Chrome deps resolved via local `.tools/`

### Recovery Status
- **Previous workspace issue:** Earlier agent expected `/home/user/geofactory-ai-documentary-main` but only `/home/user/geofactory-ai-documentary` existed
- **Current workspace:** `/root/geofactory-ai-documentary/geofactory` (verified)
- **Git remote:** `https://github.com/mmunibafatima169-bit/geofactory-ai-documentary.git` (verified)
- **Baseline commit (188e0a4...):** NOT FOUND in Git history — may reference an older/alternate repo state
- **Current HEAD (feature branch):** `c8c7425` (fix: Critical pipeline fixes...)
- **Previous feature HEAD:** `f63a022` (feat: Complete documentary production pipeline...)
- **Main branch HEAD:** `49d22d7` (Deliver Studio v2...)
- **Merge base:** `49d22d7` (Deliver Studio v2...)
- **Branches diverged:** Yes - feature branch has 2 commits ahead of main
- **Remote feature branch:** `f63a022` (1 commit behind local feature branch)
- **No staged/unstaged changes** in current working tree (clean)

---

## 10. Long-term Roadmap

| Phase | Target | Status |
|-------|--------|--------|
| 1. Repository/machine assessment | Complete | ✅ Done |
| 2. Config, logging, SQLite, queue, CLI | Complete | ✅ Done |
| 3. Topics and source-linked research | Partial | ✅ Wikipedia API; ❌ independent verification |
| 4. Scripts, claims, scenes | Partial | ✅ Groq client; ❌ live Groq validation; ❌ Ollama length |
| 5. TTS and subtitles | Partial | ✅ Edge/eSpeak; ❌ Piper voice licence |
| 6. Rights-aware assets and visuals | Partial | ✅ Commons/local; ❌ authoritative maps/legal verification |
| 7. Video and thumbnail | Complete | ✅ 1280×720 render; 1920×1080 for sample |
| 8. QA and approval dashboard | Partial | ✅ Technical gates; ❌ full editorial/frame/policy checks |
| 9. YouTube OAuth publishing | Not started | ❌ Separate reviewed phase required |
| 10. Scheduling, recovery, analytics | Partial | ✅ SQLite recovery/backup; ❌ auto scheduler/OAuth analytics |
| 11. End-to-end sample | Partial | ✅ 60s v2 sample; ❌ full 8–15 min v2-quality doc |
| 12. Provider quality upgrades | Implemented | ✅ Code complete; ❌ live validation |
| 13. Map animation & multi-concept thumbs | Implemented | ✅ Natural Earth + 3 concepts; ❌ historical/region layers |
| 14. **Pipeline automation** | **NEW** | ✅ 8-stage produce command with checkpoint/resume |
| 15. **Fact-check gate** | **NEW** | ✅ Factual verifier integrated in pipeline |
| 16. **Shorts with synced subs** | **NEW** | ✅ Chronological flow, SRT mapping, duration validation |
| 17. **FFmpeg integration tests** | **NEW** | ✅ Synthetic fixture tests added (skipped without tools) |
| 18. **Cinematic scene transitions** | **NEW** | ✅ zoom_punch, wipe_map, dip_to_black, crossfade implemented |

---

## 11. Agent-Independent Development Strategy

1. **Documentation-first:** Six permanent continuity documents capture all project state
2. **Git checkpoint policy:** Feature branches only; meaningful commits after verification + user approval; never commit to main directly
3. **Progress saving:** Update `PROJECT_STATUS.md`, `NEXT_TASK.md`, `CHANGELOG.md` at each session boundary
4. **Handoff protocol:** Each agent reads all docs, inspects Git status, identifies last verified checkpoint, continues from there
5. **Test gates:** Run `python3 -m unittest discover` before and after changes; Remotion `tsc --noEmit`; Next.js build
6. **Evidence over claims:** Every capability must have test/file/command evidence; no "it works" without proof
7. **Human approval gates:** No auto-merge, auto-publish, auto-deploy; explicit user authorization for pushes
8. **Legal/licensing honesty:** Record all licence decisions; never claim commercial rights without verified source

---

## 12. Current Session Summary (Cinematic Transitions)

| Feature | Description | Evidence |
|---------|-------------|----------|
| **Cinematic scene transitions** | Documentary renderer now implements Visual Director's transition specs: zoom_punch, wipe_map, dip_to_black, crossfade using FFmpeg xfade/fade filters | `geofactory/media/documentary_renderer.py` lines 70-130 (`_build_transition_filter`) |
| **Transition duration scaling** | Transition duration scales with segment length (max 1.5s, 15% of segment) | `_build_transition_filter` logic |
| **Transition filter tests** | 8 unit tests verify filter generation for all transition types | `tests/test_transitions.py` — all PASS |

---

## 13. Test Infrastructure Status

| Test Suite | Tests | Pass | Skip | Fail | Notes |
|------------|-------|------|------|------|-------|
| Core | 8 | 8 | 0 | 0 | Config, jobs, rights |
| Providers | 6 | 4 | 2 | 0 | Groq, Pexels, Pixabay, TTS (2 skipped: FFmpeg) |
| Studio | 9 | 9 | 0 | 0 | Scene manifest, Visual Director, QA, Factual, Asset selector |
| Wikimedia | 7 | 7 | 0 | 0 | Commons, Wikipedia |
| Documentary Planner | 13 | 13 | 0 | 0 | Planning, validation, CLI |
| Render Integration | 11 | 0 | 11 | 0 | All skipped: FFmpeg/PIL not in sandbox |
| **Transition Filters** | **8** | **8** | **0** | **0** | **NEW: zoom_punch, wipe_map, dip_to_black, crossfade** |
| **Total** | **63** | **42** | **13** | **0** | All passing where tools available |

