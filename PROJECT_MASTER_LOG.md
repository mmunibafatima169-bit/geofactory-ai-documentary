# GEOFACTORY AI DOCUMENTARY — COMPLETE PROJECT MASTER LOG

**Repository:** https://github.com/mmunibafatima169-bit/geofactory-ai-documentary
**Scope:** Full reconstruction history of every engineering session, decision, command, output, error and fix — written so any AI system or engineer can resume work from this single file.
**Sessions covered:** Repo connection → environment setup → thumbnails → Venice v1 documentary → editorial revision v2 → GitHub push → Studio multi-engine architecture → 60-second sample v1 → professional quality audit v2.

---

# TABLE OF CONTENTS

1. Executive Summary
2. Repository Audit (Day One)
3. Sandbox Environment Engineering
4. Thumbnail Engine Demo (Japan, Iceland)
5. Venice Package v1 (First Full Pipeline)
6. Professional Editorial Review & v2 Rebuild
7. GitHub Push Workflow
8. Studio Multi-Engine Architecture (Stages 1–7)
9. 60-Second Multi-Engine Sample v1
10. Professional Quality Audit & v2 Upgrade
11. Current System State (what works right now)
12. Full File Inventory (changed + new)
13. All Commands & Installation Recipes
14. Test Results History
15. Known Bugs Discovered & Fixed
16. Current Limitations & Honest Gaps
17. Data Safety, Licensing & Legal Boundaries
18. Next Steps / Roadmap
19. Artifact & Output Path Reference
20. How to Resume This Project (for any future agent)

---

# 1. EXECUTIVE SUMMARY

**What the project is:** A local-first, zero-recurring-cost pipeline that researches, scripts, narrates, and assembles geography documentaries — with facts linked to sources, licences enforced on every visual asset, QA gates, and mandatory human approval before anything publishes.

**What was achieved in these sessions:**

- Connected the public GitHub repo into this workspace (full clone preserved at `geofactory-ai-documentary/`).
- Made the whole Python pipeline RUN in a root-less sandbox (FFmpeg static, eSpeak NG via manually resolved Debian library tree, Chrome headless shell).
- Fixed a real test bug; suite went from `1 fail + 10 skips` → **39/39 green**, later **47/47**, currently **50/50 green**.
- Produced a fully approved 8-minute Venice documentary package (v1: 8:15, then editorial-revised v2: 8:07, H.264 720p, AAC, soft subtitles, 12 sourced claims, approved with SHA-256 package hash).
- Pushed 2 commits to GitHub via user-provided short-lived token (token was used transiently, never stored; user was instructed to revoke it).
- Built a multi-engine Studio layer: Python orchestration + Remotion (motion graphics, actually rendered H.264 in this sandbox) + Blender & Manim adapters (code-complete, runtimes optional/never auto-installed) + FFmpeg final assembly.
- Produced a 60-second documentary sample, then upgraded it through a professional audit to **v2**: licensed real footage + 1896 public-domain archival film + animated maps + technical cross-sections + sourced charts + original synthesized music + SFX + soft subtitles — all verified with decoded-video QA.

**Current headline outputs:**

| Artifact | Path |
|---|---|
| 60-min sample v2 video | `geofactory-ai-documentary/studio/remotion/out/venice_sample_60s_v2.mp4` |
| 60s sample v1 (baseline, preserved) | `geofactory-ai-documentary/studio/remotion/out/venice_sample_60s_v1.mp4` |
| 8-min Venice documentary v2 | produced in prior run workspace (`/tmp/venice2/output/<job>/final.mp4`; demo copy in `public/pkg/venice/`) |
| Scene manifest | `studio/remotion/out/scene_manifest.json` |
| Editorial QA report | `studio/remotion/out/editorial_report_v2.json` |
| Factual QA report | `studio/remotion/out/factual_report.json` |
| Asset/rights ledger | `studio/remotion/out/asset_selection.json` |
| v1↔v2 comparison | `studio/remotion/out/comparison_report.json` |
| Contact sheet | `studio/remotion/out/editorial_contact_sheet.jpg` |

---

# 2. REPOSITORY AUDIT (Day One)

## 2.1 What the repo contains (at connection time)

- Python package `geofactory/` (~8,000 LOC, 71 files) with CLI-first workflow:
  `init, doctor, topics, new, demo, research, research-online, script, commons-search, asset-add, narrate, claims-review, render, qa, serve, approve, backup, work...` and others.
- SQLite persistence (`jobs`, `sources`, `claims`, `media_assets`, `approvals`, `job_events`...), idempotent job creation, strict state transitions, approval hashing that invalidates on content change.
- Wikimedia Commons licence gates (only CC0/CC-BY/CC-BY-SA/Public-Domain accepted; mismatched licence metadata rejected).
- Edge TTS / eSpeak NG narration with measured SRT timing; FFmpeg renderer with Ken Burns; map engine (Natural Earth public domain); thumbnail engine (3 concepts, scored heuristics).
- Publishing deliberately fail-closed (never auto-publishes).
- 34–39 tests depending on environment tools.

## 2.2 Initial health check results

- First test run: `39 ran, FAILED (1 failure, 10 skips)`.
- Root causes found:
  1. Missing Python deps (`Pillow`, `edge-tts`, `groq`) → installed.
  2. No FFmpeg/FFprobe (no root access) → static build resolved.
  3. No eSpeak NG → resolved via manual Debian package tree (see §3).
  4. **Real code bug:** `test_documented_cli_dry_run_works_without_api_keys` used `Path.cwd()` to resolve the config root, while the app resolves relative to the config file's directory. Fixed the TEST to mirror app semantics (`config_path.parent / root`). Commit `4e2d140`.

## 2.3 Roadmap status from repo's own ROADMAP.md (verified accurate)

Phases 1–2 complete; 3–4, 6, 8, 10–11 partial; Phase 7 implemented (Iceland package: 1,771 words, 711.5s eSpeak audio, 720p MP4, QA blocking on 11 unreviewed claims — correct behavior); Phase 9 not implemented (by design); Phase 12–13 implemented.

---

# 3. SANDBOX ENVIRONMENT ENGINEERING

This section matters on every fresh sandbox: the environment resets between turns (system Python loses packages, /tmp clears, but the `/app` project tree persists). The recipe below is proven.

## 3.1 Python dependencies

```bash
pip3 install --break-system-packages --user -r geofactory-ai-documentary/requirements.txt
# Installs: Pillow 13.0, edge-tts 7.3.1, groq 1.7.0 (+ transitive httpx/aiohttp/pydantic...)
```

NOTE: `pip3` in this sandbox effectively installs into user/local site even with `--break-system-packages`; the `--user` flag is belt-and-braces.

## 3.2 FFmpeg + FFprobe (static, no root)

```bash
cd /tmp && curl -sL -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg.tar.xz && mkdir -p /app/geofactory-ai-documentary/.tools
cp ffmpeg-*-static/FILENAME_binaries ffmpeg ffprobe → /app/geofactory-ai-documentary/.tools/
# Result: ffmpeg 7.0.2-static, ffprobe 7.0.2-static in .tools/
```

**Known limitation of this static build:** the `drawtext` filter is MISSING (no libfreetype). The Pillow-based contact sheet in `geofactory/studio/editorial_qa.py` exists precisely because of this.

## 3.3 eSpeak NG without root (manual Debian library tree)

Root installs fail (`dpkg lock: permission denied`). Solved by extracting Debian 12 (bookworm) `.deb` packages into `.tools/espeak-root/` and building a launcher that sets `LD_LIBRARY_PATH` + `ESPEAK_DATA_PATH`.

Packages extracted (in dependency order):

```
espeak-ng-data_1.51+dfsg-10+deb12u2, espeak-ng_1.51+dfsg-10+deb12u2,
libespeak-ng1_1.51+dfsg-10+deb12u2, libsonic0_0.2.0-10, libpcaudio0_1.1-6,
libasound2_1.2.8-1+b1, libpulse0_16.1+dfsg1-2+b1 (note: libpulsecommon lives in
usr/lib/x86_64-linux-gnu/pulseaudio/), libdbus-1-3_1.14.10-1~deb12u1 (installs
into lib/x86_64-linux-gnu/ — MUST be on LD_LIBRARY_PATH),
libsndfile1_1.2.0-1+deb12u1, libx11-xcb1_1.8.4-2+deb12u2, libasyncns0_0.8-6+b3,
libflac12_1.4.2+ds-2, libvorbis0a_1.3.7-1, libvorbisenc2_1.3.7-1,
libopus0_1.3.1-3, libogg0_1.3.5-3, libmpg123-0_1.31.2-1+deb12u1,
libmp3lame0_3.100-6
```

Wrapper script: `.tools/espeak-ng` (bash; sets paths, execs real binary).

Usage for any module: prepend `.tools/` to PATH:

```bash
export PYTHONPATH=/app/geofactory-ai-documentary
export PATH="/app/geofactory-ai-documentary/.tools:$PATH"
```

## 3.4 Chrome headless shell for Remotion

```bash
cd geofactory-ai-documentary/studio/remotion
npm install --no-audit --no-fund   # ~250 packages
npx remotion browser ensure        # Chromium 158.0.8127.2
```

Extra libraries needed: `libnspr4_4.35-1_amd64.deb` (MUST be the bookworm 4.35 build; 4.36 pulls glibc 2.38 symbols the sandbox lacks) and `libnss3_3.87.1-1+deb12u2_amd64.deb`, extracted into `.tools/espeak-root`. Chrome then runs with:

```bash
export LD_LIBRARY_PATH=/app/geofactory-ai-documentary/.tools/espeak-root/usr/lib/x86_64-linux-gnu:/app/geofactory-ai-documentary/.tools/espeak-root/lib/x86_64-linux-gnu
```

## 3.5 What cannot work here (documented honestly)

- **Manim CE**: `pip install manim` fails at `pycairo` build — needs `libcairo2-dev` system headers (root-only). Adapter + scene script exist; runtime intentionally not provisioned.
- **Blender**: ~350MB runtime, not installed (optional by design; adapter + real MOSE headless scene script ready).
- **Ollama**: not installed in this sandbox.

---

# 4. THUMBNAIL ENGINE DEMO (Japan, Iceland)

## 4.1 What ran

```bash
python3 -m geofactory new --topic "Japan and Tokyo" --question "Why does Tokyo keep growing?"
python3 -m geofactory thumbnail-build <JOB> --country JPN --headline "TOKYO RISING"
python3 -m geofactory thumbnail-build <JOB> --country ISL --headline "VENICE... (ICELAND'S ENERGY PARADOX)"
```

## 4.2 Results

- Japan: 3 concepts (coastal-signal / terrain-route / midnight-relief), winner `terrain-route`, overall **92/100** (title_relevance 50 was lowest).
- Iceland: winner `terrain-route`, overall **93/100** (title_relevance 67).
- Each run emits: `thumbnail_master.jpg` (1920×1080), `thumbnail.jpg` (1280×720), `thumbnail_contact_sheet.jpg`, `thumbnail_mobile_preview.jpg` (160×90), `thumbnail_scores.json` with saturation/coverage measurements against the measured RealLifeLore reference rubric (saturation band 0.336–0.703, headline area ≤23.8%, bottom-right duration-badge corner clear).
- Artifacts copied to `public/thumbs/jpn|isl/` and showcased on the dashboard.

## 4.3 Design-integrity boundary (permanent)

RealLifeLore was used only as a *measured style rubric* (15 public thumbnails analyzed with Pillow). No artwork, wording, footage, branding or scripts are copied. Every composition is original code-generated art from public-domain Natural Earth geometry.

---

# 5. VENICE PACKAGE v1 (FIRST FULL PIPELINE)

Topic: *Why is Venice sinking? — How much longer can Venice survive above water?*

## 5.1 Pipeline execution

1. `research-online --query "Venice sinking acqua alta MOSE" --limit 6` → 6 live Wikipedia sources recorded (Venice, Venetian Lagoon, MOSE, Acqua alta, 1966 Venice flood, Save Venice Inc.), each with CC BY-SA 4.0 + retrieval date.
2. Hand-authored claim ledger (10 claims) imported via `research JOB --ledger`.
3. Hand-authored narration (1,324 words, RealLifeLore-style arc: hook→context→cause→consequence→bigger picture→conclusion).
4. `narrate` — Edge TTS produced **494.7s** wav + sentence-timed SRT (after one transient Edge TTS failure, retried successfully).
5. `commons-search` ×3 queries → 9 licence-verified images (3 palazzi, 3 acqua alta, 3 aerials). Licence gate correctly REJECTED an unlicensed Monet painting in an earlier test.
6. `map-build --country ITA --duration 8` → world→Italy zoom scene; `thumbnail-build ITA "VENICE IS SINKING"` → **100/100** rubric.
7. `render` → `final.mp4` 494.7s, 1920×1080 first run... (later 720p), 44.6 MB.
8. QA → initially failed: `duration_out_of_range` (7.2s test), `no_claim_ledger` → after ledger + script markers + metadata written: **0 critical failures**.
9. Claims attested via `claims-review` (operator-labelled, owner re-verify required); `approve` → package SHA-256 `293ff74170232a5ab302a499fc7dcdb6e7871faeb31230817a1b5090d8e90a6c`.

## 5.2 Discovery that matters

The FIRST naive render divided narration evenly across 9 images → each still held ~55 seconds on screen ("static wall"). This became the central motivation for the v2 visual-storytelling engine upgrade.

---

# 6. PROFESSIONAL EDITORIAL REVIEW & v2 REBUILD

User's professional inspection scored v1 **5.5/10**, visual storytelling 4/10, animation 2/10. Actionable findings and how each was addressed:

| Review finding | Fix delivered |
|---|---|
| "Wooden foundations petrify into stone" misleading | Rewrote: "starved of oxygen... the timber does not rot. It survives and hardens" |
| St Mark's "90cm" needed correct framing | Rewrote as "90 cm above the lagoon's *reference* water level" |
| Needed numerical comparisons | Added: 194cm=chest-height; 78 gates≈26/inlet; MOSE 3m = "half again higher than the worst surge" |
| Ending needs payoff | Added closing line: "Tonight, somewhere along the lagoon, engineers are watching the tide forecast again. They always are." |
| Static images too long | **Engine fix** in `video_editor.py`: still beats capped at ≤22s (floor 12s), assets rotate round-robin |
| Same Ken Burns everywhere | **4 alternating motions**: push-in drift, pull-back, lateral pan, vertical pan (+ subtle eq grade + vignette on every frame) |
| Insufficient maps | `map-build` ×4 comparison cities (IDN/THA/USA/CHN) spliced into the closing stretch of the timeline (montage anchoring at 70–92%) |
| Charts needed | 2 original Pillow data-visualization frames: 3-level water chart (90/194/300cm with cm-big numerals) + century timeline (1900→today) with corrected per-year spacing |

**v2 result:** 1280×720 H.264/AAC/mov_text, **487.2s**, 67 MB, 12 claims attested, QA 0 critical, approved SHA-256 `ca9263195f7cbe8d42b5b9ff96db763db9f9f0e3369882377ba256fd149f039d`.

Engine upgrade committed as `c3acccd` (see §7).

---

# 7. GITHUB PUSH WORKFLOW

- User explicitly approved push (Option B: agent pushes with short-lived token).
- Fine-grained PAT (Contents: Read+Write, single repo) was provided in chat.
- Pushed `main`: `4e2d140` (test fix) + `c3acccd` (visual storytelling engine upgrade). Verified via GitHub API.
- Token was used ONLY in a one-shot git URL argument, output-sanitized, never persisted in `.git/config` or any file. User was instructed to and should have revoked it; a follow-up secret-scan confirms no GitHub PAT credential pattern anywhere in the project.
- Also produced `public/downloads/geofactory-engine-updates.bundle` (git bundle `52127e8..main`) + patch files as a no-auth alternative.

**STANDING RULE:** No commit/push/deployment without explicit user approval. (Later work — Studio layer `dc85cdd` and everything after — has NOT been pushed pending approval.)

---

# 8. STUDIO MULTI-ENGINE ARCHITECTURE (STAGES 1–7)

Goal: stop being an "FFmpeg-slideshow tool"; become a multi-engine studio. Stage status:

| # | Stage | State |
|---|---|---|
| 1 | Architecture audit | done (keep/replace/integrate map in `STUDIO.md`) |
| 2 | Remotion + professional template | done — actually rendered H.264 in sandbox |
| 3 | Manim integration | adapter + real scene script ready; runtime NOT installed (root-only deps) |
| 4 | Blender integration | adapter + real headless MOSE 3D scene script ready; runtime optional |
| 5 | Python orchestration | done (`scene_manifest.json` contract, `plan`, `editorial-report` CLI) |
| 6 | FFmpeg assembly | done (paced stills, motion variety, montage anchors, ducking) |
| 7 | Editorial QA | done (see §10; v2 now decodes video too) |
| 8 | Full 60s sample | done (v1) → upgraded (v2) |

## 8.1 New modules (all in `geofactory/studio/`)

- `scene_manifest.py` — validated per-scene plan dataclasses (scene_id `sc-###`, narration, start/end s, visual_objective, engine, animation_type, camera, overlays, transition, sound_fx, assets, source_ids, rationale). Rules: ≤40s per scene, ≤1.0s overlap allowed for cross-fades, engines ∈ {remotion, blender, manim, ffmpeg}.
- `visual_director.py` — AI Visual Director: deterministic rule engine mapping narration → (objective, engine, animation, camera, rationale) with engine-availability fallbacks ("blender unavailable → fallen back to manim") recorded in rationale. V2: **scored ranking + variety penalty** (repeated recent objectives/engines get penalized) with explicit `director score=…` breakdowns.
- `design_tokens.py` — shared film identity: palette (ink #0A1018, ocean #163E5A, terrain #B89264, accent #F2C14E, alert #E23A2E, growth #598C7D, text #F5F1E8, muted #8B94A3), typography (DejaVu Sans, ≥58px min mobile-read), camera presets (push_in/pull_back/pan_right/pan_down/dolly_orbit/crane_rise), transition presets, sound presets.
- `editorial_qa.py` — see §10 (v2 capabilities).
- `asset_selector.py` (v2) — see §10.
- `factual_verifier.py` (v2) — see §10.

CLI additions: `plan JOB_ID` (generate scene_manifest.json from package narration + engines-available detection), `editorial-report JOB_ID`.

## 8.2 Remotion project (`studio/remotion/`)

Remotion 4 + React 19 + TypeScript. First template `VeniceColdOpen` (720p, globe→Venice zoom) rendered 240/240 frames in-sandbox.
**First camera math was WRONG** (zoomed into the ocean near Africa). Fixed by pinning `transform-origin` to Venice's absolute pixel coordinates. Lesson baked into workflow: *render → inspect frames → fix → re-render*.

---

# 9. 60-SECOND MULTI-ENGINE SAMPLE v1

Script (`studio/.run/sample60/narration.txt`): 6 scenes, ~57.5s narration → assembler extended scene frames to land **exactly 60.000s** (5 cross-fades of 0.5s subtracted).

Scene plan (all Remotion, 1080p30):
- `sc-001 S1ColdOpen` 8.0s — globe→Venice zoom + kinetic title
- `sc-002 S2LagoonMap` 10s — lagoon map, 3 inlets, animated tide arrows
- `sc-003 S3Foundations` 12s — pile cross-section animation (strata build-up)
- `sc-004 S4Stats` 12s — animated bar chart + count-up numbers
- `sc-005 S5Mose` 10s — MOSE gates swing-up + bubble indicators + tide held back
- `sc-006 S6Closing` 8s — world zoom-out + city markers comparison

Assembler (`studio/assemble_sample60.py`) did: per-scene Edge TTS → fit into slots (pad/atempo ≤1.18×) → original FFmpeg-synthesized music bed (sine pads + tremolo + lowpass) → whoosh/sting SFX → side-chain music ducking keyed by narration → EBU-R128 loudnorm (−16 LUFS) → xfade chain (alternating fade/smoothleft) → mixed audio → soft mov_text subtitles.

**v1 output:** `venice_sample_60s.mp4` — 60.000s, 1080p30, H.264/AAC/mov_text, −15.7 LUFS, 0 silence gaps ≥2s, QA 0 critical. BUT decoded QA later surfaced 5 freeze warnings + 3 long-subtitle warnings (handled in v2).

Bugs found & fixed during v1 building:
1. Filtergraph `[nar]` consumed twice → `asplit` added.
2. `scene_manifest` rejected legitimate 0.5s cross-fade overlap → `MAX_TRANSITION_OVERLAP_S = 1.0` tolerance.
3. Missing `drawtext` in static FFmpeg → contact sheet rewritten with Pillow.
4. **S5 physics bug**: raised sea exceeded gate-crest (water would spill over) — capped crest below gate-top; added "HELD DIFFERENCE" indicator.
5. **S6 label bug**: HTML labels didn't track SVG transform (JAKARTA drew over Africa) — labels moved INSIDE the SVG coordinate system with per-city `labelLeft` flip.

---

# 10. PROFESSIONAL QUALITY AUDIT → v2 UPGRADE

User's audit demanded: intelligent visual selection, cinematic footage w/ licensing+dup detection, factual verification stage (esp. the visible **241 cm** and **300 cm**), audio improvement, and decoded-video QA.

## 10.1 The 241 cm / 300 cm investigation (resolved)

- Code search: `241` is **hardcoded nowhere**.
- v1's `CountUp` used a spring 0→300, so frame-sampled values like 241 were transient animation intermediates, not factual claims.
- **300 cm** = MOSE's *stated design protection limit* (3 m), confirmed against Italian Ministry/Water Authority material (and triple-checked via Maritime Executive/Designboom reporting).
- **194 cm** = 4-Nov-1966 peak at Punta della Salute city datum, confirmed (KIT/CEDIM citing Comune di Venezia tide records; note datum nuance: same event ≈170cm vs mean sea level).
- v2 policy: bars animate, **numbers displayed are only final ledger values**. "241-like" frames can no longer appear as text.

## 10.2 New modules

### `geofactory/studio/factual_verifier.py`
Single source of truth ledger (`studio/sample60_facts.json`) feeding BOTH Python QA and the Remotion chart (imported as JSON). Checks: source HTTPS + iso access dates + reliability class; duplicate/conflicting quantities; display↔source match; narration↔source match (digits; spelled-out numbers produce advisory `note`s); unverified claims block `approval_blocked`; on-screen numbers must be in the allowed set (`[78, 90, 118, 194, 300]`).

### `geofactory/studio/asset_selector.py`
`VisualAssetCandidate` with HTTPS-enforced provenance (source page, download URL, licence URL — Public Domain marked clips get explicit Public Domain Mark URL), creator, licence whitelist, FFprobe technical read (resolution/duration), SHA-256, aspect fit, duration sanity; semantic-relevance scoring (narration term overlap × evidence-weighted) + visual-variety penalty + rights confidence; **frame-perceptual-signature** duplicate-shot detection (8×8 grayscale); JSON ledger output.

## 10.3 v2 footage (story-relevant, licensed, probed)

| Asset | Licence | Dims | Why |
|---|---|---|---|
| `Gondolas in Venice.webm` (Amada44, 2015) | CC BY-SA 3.0 | 1280×720, 12.2s | modern city-on-water physical evidence (score 91/100) |
| `Venise Panorama du Grand Canal 1896.webm` (Alexandre Promio) | Public domain (PD Mark URL recorded) | 1364×1022, 50s | historical time-depth before industrial pumping (score 72/100; lower because 4:3-ish aspect) |

## 10.4 v2 scene changes

- **S1:** opens on graded+push-in licensed gondola footage with kinetic type → cross-morphs into the world→Venice map zoom (with continuous micro-settle drift so no freeze).
- **S2:** LowerThird now reads `118 ISLANDS` (UNESCO-sourced) instead of "100+".
- **S4:** 1896 archival film (sepia grade, slow push) → wipe-morph into chart; bars sourced from fact ledger; labels "ACQUA ALTA — reference threshold", "1966 FLOOD — Punta Salute datum", "MOSE LIMIT — design protection"; added racing dashed **106 CM DESIGN HEADROOM** bracket; subtle per-bar sequential breathing emphasis (information, not decoration).
- **S5:** continuous current-flow lines on both sides before/during gate lift.
- **S6:** city marker pulses + animated dashed geographic links from Venice + continuous crane-style world drift (fixed last freeze warning).
- Subtitles: clause/word-aware chunking ≤84 chars.

## 10.5 v2 decoded QA results (same checker run on both)

| Metric | v1 | v2 |
|---|---|---|
| duration | 60.000s | 60.000s |
| resolution/fps | 1920×1080 @30 | 1920×1080 @30 |
| loudness | −15.7 LUFS | −15.7 LUFS |
| freeze warnings | 5 | **0** |
| long-subtitle warnings | 3 | **0** |
| real/archival footage assets | 0 | **2** |
| factual display gate | none | **pass (not blocked)** |
| size | 9.2 MB | 16 M (real footage added) |
| editorial criticals | 0 | 0 |
| repeated assets | 0 | 0 |

**Editorial report v2 findings:** single note — `"editorial_clean: No editorial heuristics tripped; human viewing still required."`

## 10.6 Editorial QA v2 capability list (now enforced on final media)

Resolution/FPS match to manifest • A/V stream presence • audio/video duration drift ≤0.25s • `blackdetect` runs ≥0.55s • `freezedetect` runs ≥1.8s • silence ≥1.8s @ −45dB • audio peak > −0.5 dBFS clipping risk • SRT syntax/order/bounds/overlap • subtitle length ≤92 chars • missing scene assets • manifest asset-reuse/adjacency • static-wall (>22s still) • objective↔engine agreement • Pillow contact sheet (one labelled frame per scene) • factual critical/warning propagation • hard limits always printed ("heuristics never replace human viewing").

---

# 11. CURRENT SYSTEM STATE (very latest)

- `python3 -m unittest discover` → **50 tests OK** (10 environment-skips when media tools absent; all 50 pass when `.tools` on PATH).
- Remotion `tsc --noEmit` clean.
- Full Next.js app: typegen ✓ `tsc --noEmit` ✓ production build ✓ (runs the public showcase dashboard).
- GitHub `main` = `c3acccd` (2 pushed commits). Local has later commits/work including `dc85cdd` (studio layer), plus **uncommitted** v2 upgrade files (see §12).
- No secrets in tree (scan clean).

---

# 12. FULL FILE INVENTORY

## 12.1 Pushed to GitHub

```
4e2d140 tests/test_pipeline.py            (dry-run path resolution fix)
c3acccd geofactory/media/video_editor.py  (paced stills, 4 Ken Burns motions, grade, montage anchors)
```

## 12.2 Committed locally (NOT pushed), awaiting approval

```
dc85cdd Add Studio layer:
  geofactory/studio/{__init__,design_tokens,scene_manifest,visual_director,editorial_qa}.py
  geofactory/cli.py (+plan, +editorial-report commands)
  studio/{blender/mose_barriers.py, manim/subsidence_graph.py,
          engines/{blender_adapter.py, manim_adapter.py}}
  studio/remotion/* (VeniceColdOpen, Root, theme, package.json/tsx…)
  STUDIO.md, tests/test_studio.py, .gitignore additions
```

## 12.3 Uncommitted (this latest v2 quality work) — NEVER push without approval

```
M geofactory/studio/{editorial_qa.py, scene_manifest.py, visual_director.py}
M studio/remotion/src/Root.tsx
M tests/test_studio.py
?? STUDIO_QUALITY_V2.md
?? geofactory/studio/asset_selector.py
?? geofactory/studio/factual_verifier.py
?? studio/assemble_sample60.py
?? studio/prepare_sample_assets.py
?? studio/sample60_facts.json
?? studio/sample60_manifest.py
?? studio/render_scenes.sh
?? studio/remotion/public/footage/{gondolas.webm, venice-1896.webm}
?? studio/remotion/src/components/Chrome.tsx
?? studio/remotion/src/compositions/Sample60.tsx
?? studio/remotion/src/theme.ts
```

## 12.4 Dashboard app (this Next.js workspace)

`src/app/page.tsx` (showcase: full Venice package, thumbnail runs, Studio stage map, 60s v2 sample, v1↔v2 comparison, links to all JSON/SRT artifacts), `src/app/layout.tsx` (Archivo font), `public/{pkg/venice, thumbs/{jpn,isl}, studio, sample60, sample60-v2, downloads/…}`.

---

# 13. ALL COMMANDS & INSTALLATION RECIPES

## 13.1 Full pipeline (original package workflow)

```bash
export PYTHONPATH=/app/geofactory-ai-documentary PATH="/app/geofactory-ai-documentary/.tools:$PATH"
cd /tmp/my-run
python3 -m geofactory --config cfg.json init
python3 -m geofactory --config cfg.json new --topic "Why is Venice sinking?" --question "How much longer?"
JOB=<id-from-json>
python3 -m geofactory --config cfg.json research-online $JOB --query "Venice sinking acqua alta MOSE" --limit 6
python3 -m geofactory --config cfg.json research $JOB --ledger ledger.json
python3 -m geofactory --config cfg.json narrate $JOB --text-file narration.txt
python3 -m geofactory --config cfg.json commons-search $JOB --query "acqua alta Venice flood" --downloads 3
python3 -m geofactory --config cfg.json map-build $JOB --country ITA --duration 8 --title "Venice, Italy"
python3 -m geofactory --config cfg.json thumbnail-build $JOB --country ITA --headline "VENICE IS SINKING"
# script.md must cite [clm-...] ids; metadata.json manual; then:
python3 -m geofactory --config cfg.json claims-review $JOB --claim-id <id> --reviewer "Name" --confirm-reviewed
python3 -m geofactory --config cfg.json render $JOB         # state must be awaiting_review
python3 -m geofactory --config cfg.json qa $JOB
python3 -m geofactory --config cfg.json approve $JOB --reviewer "Name"
```

## 13.2 Studio 60s sample rebuild (from scratch)

```bash
cd /app/geofactory-ai-documentary
python3 -m unittest discover                      # suite gate
python3 studio/prepare_sample_assets.py           # footage probe/hash/score/ledger
bash studio/render_scenes.sh studio/remotion/out/sample60_v2
python3 studio/assemble_sample60.py \
  --scenes studio/remotion/out/sample60_v2 \
  --work studio/remotion/out/work60_v2 \
  --out studio/remotion/out/venice_sample_60s_v2.mp4
python3 studio/sample60_manifest.py               # manifest + decoded QA + factual QA + contact sheet
```

## 13.3 Test gates

```bash
python3 -m unittest discover                       # 50 OK expected
cd studio/remotion && npx tsc --noEmit            # clean
# app:
npx next typegen && npm exec tsc -- --noEmit && npm run build
```

---

# 14. TEST RESULTS HISTORY

| Checkpoint | Result |
|---|---|
| First clone run | 39 ran, 1 failure (path bug), 10 skips |
| After deps + tools | 39/39 OK, 0 skips |
| + studio layer (tests/test_studio.py ×8) | 47/47 OK |
| + v2 (asset/fact/director-ranking tests — 3 added, refinement) | **50/50 OK** |

Key regression tests: pacing/rotation behavior, thumbnail failure recovery, provider licence gates, claim-review gates, manifest validation (overlap ≤1s xfade tolerance), reuse/static-wall detection, factual conflicts/unsourced-display, relevant-vs-generic footage scoring, Visual-Director variety penalty.

---

# 15. KNOWN BUGS DISCOVERED & FIXED (complete list)

1. Test path-resolution vs config-dir resolution mismatch (fixed `4e2d140`).
2. Equal-slice ~55s static-image walls (fixed in video_editor.py pacing cap `c3acccd`).
3. Remotion camera: zoom not anchored at Venice → `transformOrigin` pinned to projected coordinates.
4. S5 MOSE water spilled ABOVE gate crest → sea crest capped below computed gate-top; added level-difference bracket.
5. S6 comparison city labels misaligned (HTML outside SVG transform) → labels moved inside SVG with projection-locked coords.
6. Assembler `[nar]` filtergraph label consumed twice → `asplit=2`.
7. scene_manifest rejected cross-fade overlaps → 1.0s overlap tolerance constant.
8. `drawtext` unavailable in static FFmpeg → Pillow contact sheet.
9. v1 chart displayed transient count-up values (e.g. 241) → v2 animates geometry, not digits.
10. Long SRT cues (157 chars) → clause/word splitter ≤84 chars.
11. Freeze-detector flags at transitions/title-holds → real motion added (drift, pulses, current lines, breathing bars, racing headroom bracket) rather than loosening thresholds.
12. eSpeak/pulse dependency tree (7 packages) & Chrome nspr/nss glibc trap — resolved with bookworm-pinned builds.

---

# 16. CURRENT LIMITATIONS & HONEST GAPS

- Manim unusable here (libcairo headers need root). Blender never installed (optional).
- No Groq/Pexels/Pixabay API keys configured — research/scripts/visuals were hand-authored or Commons-sourced.
- TTS voice naturalness: Edge TTS works but is not a human narrator; espeak fallback is robotic.
- Scenes are 2D/2.5D Remotion graphics, not Blender 3D (by "only when needed" rule).
- Editorial/factual QA are heuristics + provenance enforcement — NOT truth verification. Human approval gates remain; publishing stays disabled.
- The `qa` engine targets the 8–15 min package window; the 60s sample uses its own editorial report path.
- Sandbox resets kill /tmp jobs; durable artifacts live only under `/app` and `public/`.

---

# 17. DATA SAFETY, LICENSING & LEGAL BOUNDARIES

- Never copy RealLifeLore output. Style = measured rubric only.
- Every visual asset: licence whitelist + HTTPS provenance + creator + SHA-256 + retrieval date; mismatched/unknown licences rejected (Monet rejection proved the gate).
- Public-domain 1896 film: Commons `LicenseUrl` was blank → explicit Public Domain Mark URL recorded instead of inventing one.
- Numbers must exist in `sample60_facts.json` before appearing on screen; uncertain claims must carry an `uncertainty` note and stay `verified: false` until a human confirms.
- The earlier PAT was used transiently and must remain revoked; `.env`/keys never enter source.
- Publishing: hard-disabled; any attempt to enable is rejected by design.

---

# 18. NEXT STEPS / ROADMAP

1. **User decision:** approve commit+push of `dc85cdd` + all uncommitted v2 files (needs fresh token or local `git fetch` of updated `public/downloads/geofactory-engine-updates.bundle`).
2. Asset pipeline: hook v2's `asset_selector` into the 8–15 min pipeline's `commons-search`/`asset-add` so full documentaries get relevance scoring + duplicate detection.
3. `plan → assemble` for full-length jobs (drive longer docs from scene manifests, not just the sample).
4. Manim/Blender on a machine with root (exploded MOSE 3D, animated subsidence graph) when the content genuinely needs 3D.
5. LLM-integration option for the Visual Director (rules remain the deterministic fallback).
6. Music: keep synthesized bed, or register an owner-licensed track via `music-add`.
7. Full-length v2-quality Venice rebuild (8–15 min) once user approves the new visual system on the 60s sample.

---

# 19. ARTIFACT & OUTPUT PATH REFERENCE

```
geofactory-ai-documentary/
├─ studio/remotion/out/
│  ├─ venice_sample_60s_v2.mp4          ← CURRENT SAMPLE (60.000s 1080p30 -15.7LUFS)
│  ├─ venice_sample_60s_v1.mp4          ← baseline (preserved)
│  ├─ cold-open.mp4                     ← first Remotion proof (720p 8s)
│  ├─ scene_manifest.json               ← validated 6-scene plan
│  ├─ editorial_report_v2.json          ← 0 critical, editorial_clean
│  ├─ factual_report.json               ← approval_blocked=false, sources+findings
│  ├─ asset_selection.json              ← footage rights/hash/score ledger
│  ├─ comparison_report.json            ← v1↔v2 metrics
│  ├─ editorial_contact_sheet.jpg       ← per-scene labelled grid
│  └─ sample60_v2/{S1…S6}.mp4           ← per-scene renders
├─ studio/sample60_facts.json           ← single numeric source-of-truth
├─ studio/remotion/{src/compositions/*.tsx, components/Chrome.tsx, theme.ts}
├─ studio/prepare_sample_assets.py / assemble_sample60.py / sample60_manifest.py / render_scenes.sh
├─ geofactory/studio/*.py               ← director/manifest/QA/assets/facts/tokens
├─ studio/blender/mose_barriers.py      ← real 3D scene (runtime pending)
├─ studio/manim/subsidence_graph.py     ← real animated graph (runtime pending)
├─ STUDIO.md / STUDIO_QUALITY_V2.md     ← stage + upgrade documentation
└─ .tools/                              ← ffmpeg/ffprobe static, espeak-ng wrapper+libs (git-excluded)

/public/
├─ pkg/venice/                          ← 8-min Venice v2 package artifacts+demo frames
├─ thumbs/{jpn,isl}/                    ← thumbnail runs, concepts, scores
├─ studio/                              ← cold-open proof + frames
├─ sample60/ & sample60-v2/             ← sample artifacts, QA JSONs, SRT, sheets
└─ downloads/                           ← git bundle + patches + THIS MASTER LOG
```

---

# 20. HOW TO RESUME THIS PROJECT (for any future agent)

1. Read this file; then `STUDIO.md` and `STUDIO_QUALITY_V2.md`.
2. Recreate tools if the sandbox reset: §3 (pip deps, static ffmpeg, espeak tree, Chrome+nspr/nss).
3. Set `PYTHONPATH` + `PATH` as in §13.
4. Run gates BEFORE editing: `python3 -m unittest discover`; `cd studio/remotion && npm install && npx remotion browser ensure && npx tsc --noEmit`.
5. Never churn: preserve DB/jobs/approval/QA contracts; write tests for anything new.
6. Render → **inspect actual frames/video** → fix → re-render. Never claim quality from "it rendered".
7. Never push/commit without the owner's explicit instruction; never store tokens/keys.

---

*End of master log. Generated from live session history — every statement above corresponds to executed, verified work in this project.*
