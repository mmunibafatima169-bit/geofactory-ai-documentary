# GeoFactory AI Documentary — Master Context

**Repository:** https://github.com/mmunibafatima169-bit/geofactory-ai-documentary
**Workspace:** /root/geofactory-ai-documentary/geofactory
**Current HEAD:** 49d22d7f2989a7f2b081922741333a0dc6883cc1 (Deliver Studio v2 with rendered 60-second documentary sample)
**Branch:** main

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
          +-- quality/qa_engine.py (technical/evidence/rights release gates)
          +-- scheduler/worker.py (sequential offline package and recovery)
          +-- analytics/feedback.py (owner CSV import, descriptive summary)
          +-- publishing/youtube_client.py (deliberately fail-closed)
          |
          +-- studio/scene_manifest.py (validated per-scene production plan)
          +-- studio/visual_director.py (AI Visual Director: deterministic rules → engines)
          +-- studio/design_tokens.py (shared palette/typography/camera/transition/sound presets)
          +-- studio/editorial_qa.py (decoded-video QC: freeze/black/silence/AV drift/SRT/factual)
          +-- studio/asset_selector.py (relevance scoring, duplicate detection, rights ledger)
          +-- studio/factual_verifier.py (single source-of-truth numeric ledger for on-screen numbers)
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
| Testing | unittest (50 tests, 10 environment-skips without media tools) |

**Optional providers** (require API keys in ignored `config.json`):
- Groq (`llama-3.3-70b-versatile`) for script generation
- Edge TTS (Microsoft, via community `edge-tts` package)
- Pexels API (stock video)
- Pixabay API (stock video; no public music endpoint)

---

## 4. Production Workflow

```
Research → Fact Verification → Script → Scene Planning → Relevant Visuals
    → Maps & Motion Graphics → Narration → Sound Design → Editing
    → Quality Assurance → Private YouTube Upload → User Approval → Publishing
```

### Detailed CLI Workflow
1. **Init**: `geofactory init` — creates local `config.json`, SQLite DB, output dir
2. **Topics**: `geofactory topics` — generates scored, deduplicated proposals
3. **New job**: `geofactory new --topic "..." --question "..."` — creates persistent job
4. **Research**: `geofactory research-online JOB_ID --query "..."` — Wikipedia API discovery
   - Records: title, HTTPS URL, publisher, access date, evidence excerpt, CC BY-SA 4.0 text licence
   - API discovery ≠ fact verification; human must check citations & use independent sources
5. **Import ledger**: `geofactory research JOB_ID --ledger path.json` — human-reviewed sources/claims
6. **Script**: `geofactory script JOB_ID` — evidence-aware draft (Groq preferred, else Ollama/manual)
   - Targets ~1,500 words (validated 1,200–1,800); claim IDs validated `[clm-...]`
   - Model prose is NOT proof; human must verify every claim
7. **Assets**: `geofactory commons-search JOB_ID --query "..."` — Wikimedia Commons images
   - Licence gate: only CC0, CC-BY, CC-BY-SA, Public Domain accepted
   - HTTPS, 25 MiB cap, image signature check, metadata verified against licence URL
   - Or `geofactory asset-add` for owner-verified local files
8. **Maps**: `geofactory map-build JOB_ID --country ISO --duration N` — Natural Earth zoom/highlight
   - Renders PNG frames → MP4 scene; sidecar records dataset, version, licence, hash
   - Every map carries de-facto/disputed-status qualification
9. **Thumbnails**: `geofactory thumbnail-build JOB_ID --country ISO --headline "..."` — 3 concepts
   - Native 1920×1080 map-first masters → 1280×720 platform winner + contact sheet + 160×90 mobile preview
   - Heuristic scores (style_match, mobile_readability, contrast, text_size, geographic_accuracy, title_relevance)
10. **Narration**: `geofactory narrate JOB_ID --text-file path.txt` — chunked TTS + measured SRT
    - Sentence chunks decoded/checked for near-silence; SRT timed from measured audio
    - Manifest hashes exact text + WAV + SRT; `tts_backend: none` saves labelled text-only script
11. **Claims review**: `geofactory claims-review JOB_ID --claim-id ID --reviewer "..." --confirm-reviewed`
    - Owner attests each claim after personally checking its cited evidence
12. **Render**: `geofactory render JOB_ID` — FFmpeg video-first timeline
    - Registered stock video first at actual duration, then licensed stills (Ken Burns, ≤22s beats, 4 alternating motions)
    - Optional registered music at -20 dB under narration with limiter
    - Outputs 16:9 H.264/AAC MP4 + soft SRT subtitles
13. **QA**: `geofactory qa JOB_ID` — technical + evidence + rights gates
    - Probes/decodes final A/V, checks audio peaks, duration 480–900s, resolution ≥1280×720
    - Validates SRT syntax/sync, narration manifest hashes, asset rights/attribution
    - Blocks: unreviewed claims, unknown asset rights, missing attribution, invalid map metadata, low thumbnail scores, incomplete package
    - **Automated QA cannot check every frame, fact, legal right, or platform policy**
14. **Approve**: `geofactory approve JOB_ID --reviewer "..."` — hash-bound approval
    - Dashboard also exposes exact-package approval with anti-CSRF token
    - Content change invalidates approval → returns to `awaiting_approval`
15. **Upload**: `geofactory upload JOB_ID` — **NOT IMPLEMENTED** (fails closed)

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

---

## 6. Verified Progress (as of HEAD 49d22d7)

| Component | Status | Evidence |
|-----------|--------|----------|
| Config/DB/CLI/Jobs | **VERIFIED** | All tests pass; idempotency, transitions, recovery work |
| Topic proposals | **VERIFIED** | Deterministic scoring, deduplication, history |
| Wikipedia research | **VERIFIED** | Live API discovery, CC BY-SA 4.0 recording, HTTPS enforcement |
| Claim ledger import/export | **VERIFIED** | JSON schema validation, source IDs, claim kinds |
| Script generation | **PARTIAL** | Groq client implemented; Ollama tested (74 words, failed length); no live Groq key |
| TTS (Edge/eSpeak) | **VERIFIED** | Chunked WAV, FFprobe duration, measured SRT, silence check |
| Commons search/download | **VERIFIED** | Licence gate rejects non-commercial/unknown; attribution/hash recorded |
| Asset registration | **VERIFIED** | Manual `asset-add`/`music-add` with rights attestation |
| Map animation engine | **VERIFIED** | Natural Earth cached, world→country zoom MP4, sidecar manifest, hash validation |
| Thumbnail engine | **VERIFIED** | 3 concepts, scored, contact sheet, mobile preview, JSON recipes |
| Video editor | **VERIFIED** | Video-first timeline, Ken Burns variety, music ducking, soft SRT |
| QA engine | **VERIFIED** | 50 tests pass; decode checks, A/V drift, SRT, asset rights, thumbnail rubric |
| Approval hashing | **VERIFIED** | Content change detection, invalidation, dashboard integration |
| Studio layer (Remotion) | **VERIFIED** | Cold-open rendered (8s, 720p); 60s v2 sample rendered (60.000s, 1080p30) |
| Visual Director v2 | **VERIFIED** | Ranked rules + variety penalty; engine fallback recorded in rationale |
| Editorial QA v2 | **VERIFIED** | Decoded-video checks (freeze/black/silence/AV drift/SRT/factual) |
| Factual verifier | **VERIFIED** | Single numeric ledger (`sample60_facts.json`); display↔source match |
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
| No automated scheduler | Sequential manual processing only | `geofactory work` recovers interrupted jobs; no background daemon |
| Editorial/factual QA are heuristics | Cannot certify truth or professional quality | Human full-length viewing + source review mandatory |
| Natural Earth 1:110m only | No historical borders, rivers, density, climate layers | Each layer needs independent sourced dataset before implementation |
| Sandbox resets lose `/tmp` jobs | Durable artifacts only under `/app` and `public/` | Use persistent output dirs; backup DB regularly |

---

## 8. Production Blockers

| Blocker | Severity | Description |
|---------|----------|-------------|
| **No API keys for Groq/Pexels/Pixabay** | High | Cannot validate end-to-end provider workflow (script, stock video, music) |
| **Piper voice licence not cleared** | Medium | No neural TTS option without commercial-use-verified voice model |
| **Manim/Blender runtimes unavailable** | Medium | 3D/technical scenes blocked; Remotion 2D/2.5D works |
| **YouTube upload not implemented** | High | Publishing pipeline incomplete; fail-closed by design |
| **No automated claim fact-checking** | High | All claims require manual human verification against sources |
| **Legal rights verification is owner-attested** | Medium | System records metadata; no independent legal verification |

---

## 9. Arena Merge History & Recovery Situation

### Arena Merge
- **Merge commit:** `dc85cdd` (Add Studio layer: multi-engine architecture with Visual Director)
- **Parent commits:** `c3acccd` (Upgrade visual storytelling) + Arena's unpublished changes
- **Merged changes:** Studio layer (`geofactory/studio/`), Remotion project (`studio/remotion/`), Blender/Manim adapters, editorial QA, Visual Director, scene manifest, design tokens
- **Production blockers from merge:** Manim/Blender runtimes not provisioned; Remotion requires Chrome headless + Debian libs (resolved in sandbox via local `.tools/`)

### Recovery Status
- **Previous workspace issue:** Earlier agent expected `/home/user/geofactory-ai-documentary-main` but only `/home/user/geofactory-ai-documentary` existed
- **Current workspace:** `/root/geofactory-ai-documentary/geofactory` (verified)
- **Git remote:** `https://github.com/mmunibafatima169-bit/geofactory-ai-documentary.git` (verified)
- **Baseline commit (188e0a4...):** NOT FOUND in Git history — may reference an older/alternate repo state
- **Current HEAD:** `49d22d7` (Deliver Studio v2 with rendered 60-second documentary sample)
- **Unpushed commits:** `dc85cdd` (Studio layer) + uncommitted v2 quality files (see PROJECT_MASTER_LOG.md §12)
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

---

## 11. Agent-Independent Development Strategy

1. **Documentation-first:** Six permanent continuity documents (this file + 5 others) capture all project state
2. **Git checkpoint policy:** Feature branches only; meaningful commits after verification + user approval; never commit to main directly
3. **Progress saving:** Update `PROJECT_STATUS.md`, `NEXT_TASK.md`, `CHANGELOG.md` at each session boundary
4. **Handoff protocol:** Each agent reads all docs, inspects Git status, identifies last verified checkpoint, continues from there
5. **Test gates:** Run `python3 -m unittest discover` before and after changes; Remotion `tsc --noEmit`; Next.js build
6. **Evidence over claims:** Every capability must have test/file/command evidence; no "it works" without proof
7. **Human approval gates:** No auto-merge, auto-publish, auto-deploy; explicit user authorization for pushes
8. **Legal/licensing honesty:** Record all licence decisions; never claim commercial rights without verified source

---
