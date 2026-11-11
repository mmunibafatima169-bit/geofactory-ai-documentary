# GeoFactory AI Documentary — Final Delivery & Technical Audit Report

**Audit date:** 2026-11-10  
**Repository:** `mmunibafatima169-bit/geofactory-ai-documentary`  
**Audited baseline:** `49d22d7f2989a7f2b081922741333a0dc6883cc1`  
**Working branch:** `arena/10f25b91-geofactory-ai-documentary`  
**Latest artifact:** `examples/studio-sample-v2/venice_sample_60s_v2.mp4`  
**Artifact SHA-256:** `c9a83c9bea077bdf8d3e8f827d073b0fb44091b4bb86db821781d5ca5c8e0f8d`

> **Audit stance:** this report distinguishes fresh measurements from historical project claims. The supplied MP4 was decoded and inspected; it was not re-rendered or overwritten. No commit, push, deployment, secret access, or release approval was performed.

---

## 1. Executive Summary

### What was requested

The project requested a local-first documentary-generation system and, specifically for this sample, a polished 60-second Venice documentary using Python orchestration, Remotion motion graphics, optional Manim/Blender engines, licensed footage, maps, technical animation, charts, narration, original audio, subtitles, factual traceability, and decoded-output QA. This final request asks for one independently reviewable delivery and technical-audit package.

### What is actually implemented

- A Python package covering configuration, jobs, research/script providers, asset rights, TTS, maps, thumbnails, video editing, QA, scheduling, and approval gates.
- A Studio layer with validated scene manifests, deterministic visual direction, footage selection, factual-ledger consistency checks, and editorial QA.
- Six Remotion compositions forming the 60-second sample: cold open, lagoon map, foundations, statistics, MOSE, and world comparison.
- A real H.264/AAC MP4 with English soft subtitles, two documented licensed/archival footage sources, generated vector/2D motion graphics, narration, synthesized music/SFX, ducking, loudness normalization, and crossfades.
- Python/FFmpeg assembly code and optional Manim and Blender adapters/scripts.

### What is working

- The latest MP4 exists, probes correctly, and fully decodes all 1,800 video frames and audio without errors.
- Duration, frame rate, aspect ratio, codecs, audio format, and container A/V duration alignment pass.
- No black intervals were detected at the stated threshold; no exact duplicate decoded frames were found.
- English `mov_text` subtitles exist and match the sidecar subtitle word sequence. All 22 SRT cues are sequential, bounded, non-overlapping, and at most 84 characters.
- Audio measures **−15.7 LUFS integrated** and **−4.1 dBTP**; no ≥1-second silence at −45 dB was detected. Scene-boundary RMS changes were small (0.02–1.95 dB).
- TypeScript passes `npx tsc --noEmit`.
- Existing Python suite: **50 run, 45 passed, 0 failed, 5 skipped** with FFprobe/FFmpeg supplied. A media-free run had 40 passed and 10 skipped.
- The core factual claims 118 islands, 194 cm (1966), 78 gates, and 300 cm as a design limit have credible source support.

### What is incomplete or not established

- No actual Manim or Blender render was produced; those runtimes are not installed.
- The previous v1 MP4 is absent, preventing direct before/after playback or frame comparison.
- Original raw Remotion/FFmpeg render logs and intermediate scene renders are absent. Completion is established from the valid final artifact and embedded provenance, not a retained process log.
- A clean rebuild cannot currently use the two original footage inputs because `studio/remotion/public/footage/` is intentionally not committed. The preparation script can retrieve them where network access permits.
- No ASR/forced alignment, listening review, pronunciation assessment, dictionary spelling pass, or full perceptual quality review was performed.

### Known problems

1. **Fresh frozen-frame QA fails.** The current file produces many `freezedetect` events at ≥0.5 s, including **36.033–39.100 s (3.067 s)** and **39.100–41.767 s (2.667 s)**. This contradicts the archived claim of zero v2 freeze warnings. Some holds are intentional, but the release-gate test fails.
2. **Chart layout defect.** Representative frames around 37 s and 41 s show the large `300` label crowding/clipping at the top of the MOSE bar.
3. **90 cm source mismatch.** The cited CEDIM source defines flooding/acqua alta from **80 cm**, not 90 cm. Its 90 cm table row means 2% flooded area. The current factual gate validates ledger consistency, not whether the source really supports the label.
4. **Foundation narration is too absolute.** “The timber never rotted” conflicts with expert reporting of anaerobic bacterial damage; “It hardened instead” is insufficiently supported and oversimplifies preservation.
5. Several lines are rhetorical or broader than their evidence: “most beautiful,” “the shield works,” “city stays dry,” and “only the first of many.” They need qualification or editorial treatment.

### Overall implementation status

**Functional rendered prototype; not release-approved.** The delivery is technically playable and demonstrates a real multi-stage Remotion/Python/FFmpeg workflow. It is not a finished professionally validated documentary because of the failed freeze gate, chart defect, factual wording issues, unavailable baseline/render provenance, and untested speech/listening dimensions.

---

## 2. Latest Rendered Video

All metadata below comes from fresh FFprobe output in `delivery_evidence/ffprobe_metadata.json.txt`; size and hash come from `stat`/`sha256sum` logs.

| Property | Measured value |
|---|---|
| Exact repository-relative path | `examples/studio-sample-v2/venice_sample_60s_v2.mp4` |
| Absolute path in this workspace | `/home/user/geofactory-ai-documentary/examples/studio-sample-v2/venice_sample_60s_v2.mp4` |
| Container duration | **60.000000 s** |
| Video stream duration | **60.000000 s** |
| Audio stream duration | **59.999000 s** |
| Resolution | **1920 × 1080** |
| Display / sample aspect | **16:9 / 1:1** |
| FPS | **30/1 average and nominal; 1,800 frames** |
| Video codec | **H.264 / AVC, High profile, yuv420p** |
| Audio codec | **AAC-LC** |
| Audio sample rate | **48,000 Hz** |
| Audio channels | **2, stereo** |
| Subtitle stream | **`mov_text`, English (`eng`)** |
| File size | **15,991,310 bytes** (15.99 MB decimal; 15.25 MiB) |
| Container bit rate | **2,132,174 bit/s** |
| Embedded provenance | **`Made with Remotion 4.0.541`** |
| SHA-256 | `c9a83c9bea077bdf8d3e8f827d073b0fb44091b4bb86db821781d5ca5c8e0f8d` |

### Rendering command and status

The repository documents this exact scene-render invocation:

```bash
bash studio/render_scenes.sh studio/remotion/out/sample60_v2
```

The script renders each composition with:

```bash
npx remotion render src/index.ts "$scene" "$target" \
  --concurrency=2 --log=error
```

The documented final assembly invocation is:

```bash
python3 studio/assemble_sample60.py \
  --scenes studio/remotion/out/sample60_v2 \
  --work studio/remotion/out/work60_v2 \
  --out studio/remotion/out/venice_sample_60s_v2.mp4
```

**Provenance limitation:** these are the recorded commands used by the project, not newly captured shell history. Original raw render logs are unavailable. **Completion status: completed artifact confirmed** by a valid 60-second MP4, embedded Remotion 4.0.541 metadata, and error-free full decode. The audit did not rerun rendering, so a fresh end-to-end rebuild is **NOT TESTED**.

---

## 3. Before vs After Comparison

### Evidence boundary

The previous video is documented as `studio/remotion/out/venice_sample_60s_v1.mp4`, but it is not present. Only the v2 MP4 exists. Consequently:

- **Direct v1↔v2 visual/auditory comparison: NOT TESTED.**
- The table labels repository-documented changes as **documented improvement**, not newly verified v1 observations.
- Current v2 characteristics were checked against the MP4, source code, and contact sheet.
- Historical metrics come from `examples/studio-sample-v2/comparison_report.json` and are not independently reproducible without v1.

| Area | Previous sample (documented) | Latest sample (observed/current code) | Assessment |
|---|---|---|---|
| Cinematic footage | 0 real footage assets | Modern gondolas in opening; 1896 archival footage before chart | **Documented improvement; v2 footage confirmed visually** |
| Geographical maps | Venice/lagoon and closing maps | Stylized Italy locator, lagoon/inlet diagram, world map with city links | **Continuous/link animation documented as improved; core map feature unchanged** |
| Camera movement | Push/pan/zoom treatments | Digital map drift/zoom and graphic reveals; mostly static technical scenes | **Some documented refinement; no direct baseline measurement** |
| Motion graphics | Remotion titles and diagrams | Same design system, additional information-bearing movement | **Improvement claimed; fresh QA still finds static holds** |
| 2D animations | Vector foundations, chart, MOSE | Pile build, bar geometry, gate lift, bubbles/current arrows | **Chart and MOSE motion documented as improved** |
| 3D animations | No actual Blender render | No actual Blender render; MOSE is 2D/2.5D SVG | **Unchanged / not implemented** |
| Charts & infographics | Animated numeric count-up could show 241 | Fixed 90/194/300 labels; animated bar geometry; shared JSON ledger | **Actual code/design improvement; current 300 label layout defective** |
| Transitions | Alternating fades/smooth-left crossfades | Same FFmpeg `xfade` chain | **Substantially unchanged** |
| Typography | Existing display/design system | Same typography and color language | **Unchanged; chart crowding remains a defect** |
| Subtitles | 3 readability warnings; long cues | 22 clause-level cues, ≤84 chars | **Documented improvement; v2 structural checks pass** |
| Narration synchronization | Scene-slot timing | Same scene-slot approach with micro-fades | **Fade improvement in code; speech alignment NOT TESTED** |
| Music & sound effects | Synthesized score/SFX, ducking, −15.7 LUFS | Same original mix architecture and −15.7 LUFS | **Core mix unchanged; fades added** |
| Scene variety | 6 scenes, no real footage | 6 scenes plus modern and archival footage | **Documented improvement; v2 six-scene variety confirmed** |
| Freeze warnings | 5 | Archived report says 0, but fresh v2 test finds many | **Claimed improvement not reproduced; current gate FAIL** |

Historical comparison values (not fresh v1 measurements): both versions 60.0 s, 1920×1080, 30 fps, −15.7 LUFS; v1 reportedly 5 freeze and 3 subtitle warnings; v1 reportedly no factual display gate; v2 ledger gate enabled.

---

## 4. Complete Repository Changes

### Baseline and existing implementation

The checkout began **clean** at commit `49d22d7f2989a7f2b081922741333a0dc6883cc1`. That commit contains the entire pre-existing implementation and v2 sample. `git diff --stat` and `git diff --name-status` were empty before delivery artifacts were created.

### Modified tracked files

**None.** No existing source code, video, subtitle, report, or asset ledger was edited.

### Deleted files

**None.** The previous sample was not overwritten or deleted; it was already absent from this checkout.

### Newly created delivery files

| File/folder | Purpose |
|---|---|
| `FINAL_DELIVERY_REPORT.md` | Main self-contained delivery and audit report |
| `DELIVERY_BUNDLE.zip` | Portable report, evidence, and latest MP4 package |
| `delivery_evidence/run_qa.py` | Reproducible metadata, decode, hashes, subtitles, and frame-extraction QA |
| `delivery_evidence/test_delivery_artifact.py` | Twelve new stdlib `unittest` media release-gate tests |
| `delivery_evidence/contact_sheet_latest.jpg` | Sixteen representative labelled frames |
| `delivery_evidence/frames/` | Sixteen lossless frame screenshots, including chart/MOSE/map animation views |
| `delivery_evidence/logs/` | Install, environment, test, FFprobe, render-provenance, decode, freeze/black, audio, hash, and repository logs |
| `delivery_evidence/ffprobe_metadata.json.txt` | Complete stream/container metadata |
| `delivery_evidence/embedded_subtitles.srt` | Subtitles extracted from the actual MP4 |
| `delivery_evidence/qa_summary.json` | Machine-readable fresh QA results and limitations |
| `delivery_evidence/factual_source_review.md` | Independent source review with URLs and discrepancies |
| `delivery_evidence/comparisons/README.txt` | Explains why direct before/after images are unavailable |

### Important existing code changes represented by the baseline

These are **existing committed features**, not edits made during this audit:

- `studio/remotion/src/compositions/Sample60.tsx`: six-scene visual implementation; fixed factual numeric labels while bar geometry animates.
- `studio/assemble_sample60.py`: TTS fitting, original audio synthesis, side-chain ducking, loudness normalization, subtitles, crossfades, and final mux.
- `geofactory/studio/editorial_qa.py`: manifest/editorial checks and media QA helpers.
- `geofactory/studio/factual_verifier.py`: source/claim/display/narration consistency gate.
- `studio/sample60_facts.json`: shared source and numeric claim ledger.
- `tests/test_studio.py` and other existing tests: architecture and behavior coverage.

### Git diff summary

Before delivery: **0 modified, 0 created, 0 deleted**. After delivery: only the untracked report, evidence directory, and ZIP are new. No existing working code was changed. Installation artifacts (`.venv/`, `node_modules/`) are ignored and are not source changes.

---

## 5. Installed Tools and Dependencies

### Versions observed in this audit environment

| Tool | Installed/available version | Evidence/status |
|---|---|---|
| Python | **3.11.2** | `python3 --version` |
| Node.js | **22.22.3** | `node --version` |
| npm | **10.9.8** | `npm --version` |
| Remotion currently installed | **4.0.542** | `npm list --depth=0` |
| Remotion recorded in rendered MP4 | **4.0.541** | FFprobe container comment; distinct from current install |
| TypeScript | **5.9.3** | current npm tree |
| FFmpeg audit binary | **N-47683-g0e8eb07980-static** (2018 build supplied by npm package) | full version log |
| FFprobe audit binary | **N-66595-gc2b38619c0-static** (2023 build supplied by npm package) | full version log |
| PyAV | **18.1.0** | installed for audit equivalence/support |
| Manim | **NOT INSTALLED** | `manim: command not found` |
| Blender | **NOT INSTALLED** | `blender: command not found` |
| eSpeak NG | **NOT INSTALLED on PATH** | five media tests requiring it skipped |

FFmpeg and FFprobe are different build dates because the audited npm packages bundle different upstream snapshots. No claim is made that these are the original render binaries.

### Exact installation commands executed

```bash
# First attempt failed under PEP 668; no packages were installed by it.
python3 -m pip install -r requirements.txt av numpy

# Successful isolated environment and Python installation.
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt av numpy

# Project npm dependencies, then audit-only media binaries.
cd studio/remotion
npm ci --no-audit --no-fund
npm install --no-save --package-lock=false --no-audit --no-fund \
  @ffprobe-installer/ffprobe @ffmpeg-installer/ffmpeg
```

### Newly installed Python packages

Direct project/audit packages: `edge-tts==7.3.1`, `groq==1.7.0`, `Pillow==13.0.0`, `av==18.1.0`, `numpy==2.4.6`.

Transitive packages installed: `aiohappyeyeballs==2.7.1`, `aiohttp==3.14.5`, `aiosignal==1.4.0`, `annotated-types==0.8.0`, `anyio==4.16.0`, `attrs==26.1.0`, `certifi==2026.10.23`, `distro==1.9.0`, `frozenlist==1.8.0`, `h11==0.16.0`, `httpcore==1.0.9`, `httpx==0.28.1`, `idna==3.20.0`, `multidict==7.2.1`, `propcache==0.5.4`, `pydantic==2.14.3`, `pydantic-core==2.50.4`, `sniffio==1.4.1`, `tabulate==0.10.0`, `typing-extensions==4.16.0`, `typing-inspection==0.4.5`, `yarl==1.25.1`. Full output: `delivery_evidence/logs/python_install.log` and `python_environment.log`.

### Newly installed npm packages

Top-level project packages: `@remotion/cli@4.0.542`, `remotion@4.0.542`, `react@19.3.1`, `react-dom@19.3.1`, `@types/react@19.3.0`, `typescript@5.9.3`.

Audit-only, unsaved packages: `@ffprobe-installer/ffprobe@2.1.2`, `@ffprobe-installer/linux-x64@5.2.0`, `@ffmpeg-installer/ffmpeg@1.1.0`, `@ffmpeg-installer/linux-x64@4.1.0`.

`npm ci` installed 250 packages including transitives. The complete resolved tree is in `delivery_evidence/logs/npm_inventory.json`; `package.json` and `package-lock.json` were not modified.

### Planned/configured but not installed

- **Manim:** adapter and `SubsidenceGraph` scene script only; runtime intentionally not installed because it is unnecessary for this report and can require native Cairo/Pango build dependencies.
- **Blender:** adapter and MOSE scene script only; runtime not installed.
- **Original Remotion browser/runtime:** not provisioned or used for a fresh render in this audit.
- **eSpeak NG:** not installed merely to reduce skips; not needed to audit the existing MP4.

---

## 6. Actual Engine Usage Evidence

### Python — actually used in production code and this audit

**Production orchestration:**

- `studio/assemble_sample60.py`: scene table, narration generation/fitting, SRT timing, audio/music/SFX generation, FFmpeg command construction, and final mux.
- `studio/sample60_manifest.py`: validated manifest and factual/editorial report generation.
- `studio/prepare_sample_assets.py`: footage download/probe/hash/rights selection workflow.
- `geofactory/studio/`: visual planning, asset scoring, factual checks, and QA.
- `geofactory/media/`: general pipeline maps, TTS, video editing, and thumbnails.

**Fresh audit evidence:** `delivery_evidence/run_qa.py`, `test_delivery_artifact.py`, factual consistency log, and two Python test-suite runs.

### Remotion — actually used for the supplied video

**Compositions:** `S1ColdOpen`, `S2LagoonMap`, `S3Foundations`, `S4Stats`, `S5Mose`, `S6Closing`; `VeniceColdOpen` also exists as an older reference composition but is not one of the six final scenes.

**Evidence of successful use:**

- FFprobe comment: `Made with Remotion 4.0.541`.
- Final visuals match the six compositions and source-defined graphic treatments.
- `Root.tsx` defines the exact six composition IDs, 30 fps, and 1920×1080 dimensions.
- Documented per-scene render command is shown in Section 2.

**Limitation:** no original per-scene MP4s or raw Remotion logs are present. No new composition was rendered in this audit.

### Manim — not used for a render

- `studio/manim/subsidence_graph.py` defines a planned `SubsidenceGraph` scene.
- `studio/engines/manim_adapter.py` provides invocation logic.
- **Actual rendered animation:** none found.
- **Output files:** none found.
- **Reason:** Manim is not installed; the delivered chart was implemented in Remotion, so installation was unnecessary for this audit.

### Blender — not used for a render

- `studio/blender/mose_barriers.py` defines a planned MOSE scene.
- `studio/engines/blender_adapter.py` provides invocation logic.
- **Actual rendered 3D scene:** none found.
- **Output files:** none found.
- **Reason:** Blender is not installed; the delivered MOSE sequence is 2D/2.5D Remotion SVG. A large optional runtime was not needed for this report.

### FFmpeg — actually used for assembly/encoding

The assembler implements these operations:

1. Convert/fit narration and synthesize music/SFX.
2. Mix narration with music ducking and SFX; apply `loudnorm=I=-16:TP=-1.5:LRA=11` and limiting.
3. Chain six scene videos through 0.5-second `xfade` transitions.
4. Apply final grade/sharpening and H.264 encoding (`libx264`, CRF 19, yuv420p).
5. Mux copied video, AAC 192 kbit/s audio, and English `mov_text` subtitles with fast-start.

**Success evidence:** final container identifies `Lavf61.1.100` and H.264 `Lavc61.3.100 libx264`; FFprobe sees all three streams; full decode returns 0 with empty error output. Fresh QA FFmpeg commands and logs are supplied. Original assembly stdout/stderr is unavailable.

---

## 7. Video Quality Assurance

### Commands

```bash
ffprobe -v error -show_format -show_streams -show_chapters -of json VIDEO
ffprobe -v error -count_frames \
  -show_entries stream=index,codec_type,nb_read_frames,duration -of json VIDEO
ffmpeg -v error -xerror -i VIDEO -map 0:v:0 -map 0:a:0 -f null -
ffmpeg -hide_banner -i VIDEO \
  -vf 'blackdetect=d=0.10:pix_th=0.02,freezedetect=n=-50dB:d=0.50' \
  -an -f null -
ffmpeg -v error -i VIDEO -map 0:v:0 -an -f framemd5 -
ffmpeg -hide_banner -i VIDEO -map 0:a \
  -af 'silencedetect=noise=-45dB:d=1.0,astats=metadata=0:reset=0,ebur128=peak=true' \
  -f null -
python3 delivery_evidence/test_delivery_artifact.py
```

### Results

| Check | Status | Measured result / timestamps |
|---|---|---|
| Black frames | **PASS** | No `black_start` at ≥0.10 s, pixel threshold 0.02 |
| Frozen frames | **FAIL** | Many ≥0.50 s events; longest **36.033–39.100 s (3.067 s)**, then **39.100–41.767 s (2.667 s)**. Other examples: 5.800–7.133, 18.467–19.433, 42.800–44.133, 46.167–47.400. Final event begins 59.300 s |
| Duplicate/repeated visuals | **PASS (exact-frame test)** | 1,800 decoded frames; 1,800 unique hashes; 0 consecutive exact duplicates. Editorial repetition is not fully decidable by hashes |
| Missing media assets | **PASS for supplied MP4 / FAIL for offline rebuild inputs** | Final decode has no missing-media errors. Source `public/footage/` files are absent, so a clean offline scene rebuild is not currently self-contained |
| Incorrect aspect ratio | **PASS** | DAR 16:9, SAR 1:1 |
| Resolution and FPS | **PASS** | 1920×1080, constant 30/1 metadata, 1,800 decoded frames in 60 s |
| Audio/video synchronization | **NOT TESTED for speech/lip/content sync** | Container duration delta **0.001 s PASS**; no ASR/forced alignment or listening test |
| Audio clipping | **PASS** | True peak **−4.1 dBTP**, sample peak about **−4.108 dBFS**, below −1 dB ceiling |
| Abrupt audio transitions | **PASS (limited RMS heuristic)** | 50 ms RMS changes at five scene boundaries: +1.95, +1.25, +1.47, +1.93, +0.02 dB. No large step detected; perceptual smoothness still requires listening |
| Subtitle timing | **PASS structurally / NOT TESTED against speech** | 22 cues, ordered, non-overlapping, within 0–60 s; last cue ends 59.800 s. Actual spoken alignment not measured |
| Subtitle spelling | **NOT TESTED** | No dictionary/spellchecker run. Manual transcript reading found no obvious misspelling; this is not a formal pass |
| Missing narration | **NOT TESTED for spoken content** | Audio is non-silent by the stated silence detector, but presence/correctness of every spoken sentence was not ASR-verified |
| Rendering errors | **PASS for final decode / original process NOT TESTED** | `-xerror` full decode returns 0 and no stderr. Original render logs unavailable |
| Corrupted output | **PASS** | Probe score 100, all streams decode, frame/audio counts valid |
| Silence gaps | **PASS** | No `silence_start` events at −45 dB for ≥1.0 s |
| Loudness | **PASS against project target** | Integrated **−15.7 LUFS**, LRA **3.5 LU**, target −16 LUFS |

**Interpretation:** PASS means only the stated automated test passed. The frozen-frame FAIL is not proof of encoder corruption; it identifies holds that require editorial review. Likewise, unique compressed decoded hashes do not prove that every shot is visually fresh.

---

## 8. Factual Accuracy

### Method and limitations

The transcript, chart, and major on-screen claims were compared with primary/scientific sources where available. Fresh source access date: **2026-11-10**. Detailed notes: `delivery_evidence/factual_source_review.md`. The repository verifier returned 0 critical findings, but it only checks internal consistency/provenance; independent reading found issues it does not catch.

Sources:

1. [1](https://whc.unesco.org/en/list/394/) UNESCO, *Venice and its Lagoon*; accessed 2026-11-10.
2. [2](https://whc.unesco.org/document/153362) UNESCO/ICOMOS nomination/evaluation documentation naming Lido, Malamocco, and Chioggia; accessed 2026-11-10.
3. [3](https://www.fincosit.it/fincosit/wp-content/uploads/2019/06/glf_mose.pdf) Italian Ministry/Venice Water Authority, *The Mose: What is it and how does it work*; project material, accessed 2026-11-10.
4. [4](https://nhess.copernicus.org/articles/21/2633/2021/) Lionello et al., *Natural Hazards and Earth System Sciences* 21, 2633–2641; published 2021-09-01; DOI 10.5194/nhess-21-2633-2021.
5. [5](https://www.cedim.kit.edu/download/FDA_VENICE_2019_draft_e.pdf) CEDIM/KIT, *Flooding in Venice, Italy*, Report No. 1; information as of 2019-11-19.
6. [6](https://www.bbc.com/future/article/20250324-the-ancient-forest-that-supports-venice) BBC Future, *Mud, water and wood*; published 2025-03-26.
7. [7](https://www.designboom.com/architecture/mose-flood-barrier-venice-storm-alex-10-05-2020/) Designboom, MOSE operational reports; updated 2020-12-07.

| Claim | Video value/wording | Verified value / qualification | Source | Status / mismatch |
|---|---|---|---|---|
| Venice is sinking | Sinking | Relative sea level rises through mean sea-level rise plus natural/anthropogenic subsidence; pumping-driven subsidence was curtailed | [4](https://nhess.copernicus.org/articles/21/2633/2021/) | **Verified with nuance**; avoid implying unchanged industrial subsidence |
| Most beautiful city on water | Superlative | Subjective editorial judgement | [1](https://whc.unesco.org/en/list/394/) supports cultural significance only | **Not objectively verifiable** |
| Islands | More than 100 spoken; **118** graphic | UNESCO: 118 small islands | [1](https://whc.unesco.org/en/list/394/) | **Verified; narration and graphic compatible** |
| Lagoon inlets | **3** narrow inlets | Lido, Malamocco, Chioggia | [2](https://whc.unesco.org/document/153362) | **Verified** |
| Wooden pile quantity | **Millions** | Broad estimate used by expert reporting; exact total unknown | [6](https://www.bbc.com/future/article/20250324-the-ancient-forest-that-supports-venice) | **Plausible but approximate** |
| Foundation layers | Mud/clay into firmer layer | Broadly consistent with short friction piles and resistant layer; animation is schematic | [6](https://www.bbc.com/future/article/20250324-the-ancient-forest-that-supports-venice) | **Mostly supported; schematic not literal** |
| Timber decay | “Never rotted” | Anaerobic bacteria do attack wood; decay is slower and the wood/water/soil system remains resilient | [6](https://www.bbc.com/future/article/20250324-the-ancient-forest-that-supports-venice) | **FAIL / too absolute** |
| Timber hardening | “It hardened instead” | Source does not substantiate simple petrification/hardening explanation | [6](https://www.bbc.com/future/article/20250324-the-ancient-forest-that-supports-venice) | **Unsupported / revise** |
| Groundwater pumping | Accelerated sinking until 1970s | Strong anthropogenic phase especially 1950–1970; regulation/alternative supplies avoided it since 1970s | [4](https://nhess.copernicus.org/articles/21/2633/2021/) | **Verified with wording nuance** |
| 1966 record | **194 cm** spoken and graphic | Highest recorded water height, 4 Nov 1966, 194 cm; local datum matters | [4](https://nhess.copernicus.org/articles/21/2633/2021/), [5](https://www.cedim.kit.edu/download/FDA_VENICE_2019_draft_e.pdf) | **Verified; narration/graphic agree** |
| Acqua alta reference | **90 cm** graphic | Cited CEDIM text says flood/acqua alta begins at 80 cm; 90 cm row corresponds to 2% area flooded | [5](https://www.cedim.kit.edu/download/FDA_VENICE_2019_draft_e.pdf) | **MISMATCH with cited source; relabel/source precisely** |
| MOSE gates | **78 hollow steel gates** | Four rows across three inlets; 21 + 20 + 19 + 18 = 78 | [3](https://www.fincosit.it/fincosit/wp-content/uploads/2019/06/glf_mose.pdf) | **Verified; narration/graphic agree** |
| Gate operation | Seabed, compressed air, swing upward | Water-filled gates rest on seabed; compressed air empties them and they rise to block tide | [3](https://www.fincosit.it/fincosit/wp-content/uploads/2019/06/glf_mose.pdf) | **Verified** |
| MOSE limit | **300 cm** | Design protection from tides up to 3 m; not a measured flood | [3](https://www.fincosit.it/fincosit/wp-content/uploads/2019/06/glf_mose.pdf) | **Verified with correct “MOSE LIMIT” label** |
| Shield works / city dry | Broad absolute wording | Successful real operations reported; not a permanent guarantee under every condition | [7](https://www.designboom.com/architecture/mose-flood-barrier-venice-storm-alex-10-05-2020/) | **Supported only as qualified operational statement** |
| Sea still rises | Continuing rise | Relative/global sea-level rise documented | [4](https://nhess.copernicus.org/articles/21/2633/2021/) | **Verified** |
| First of many | Venice “only the first of many” | Rhetorical warning, not a sourced chronological ranking | [4](https://nhess.copernicus.org/articles/21/2633/2021/) supports broader future risk | **Not literally verified; frame as rhetoric** |

### Specific 241 cm / 300 cm investigation

- **241 cm:** no supporting source and no hardcoded current value. Historical documentation identifies it as a transient frame in the former spring-driven 0→300 counter. Current `Sample60.tsx` keeps final labels fixed and animates only bar geometry. The latest chart does not present 241 cm as a factual value.
- **300 cm:** verified as **3 m MOSE design protection** from official project material. It must never be interpreted as a historical water-level measurement. The current “MOSE LIMIT” category is conceptually correct.
- **Remaining graphic problem:** the fixed 300 label is crowded/clipped at the top in sampled frames, so factual correction introduced a layout issue that needs repair.

---

## 9. Visual Evidence

### Primary evidence

| Exact relative path | Contents |
|---|---|
| `delivery_evidence/contact_sheet_latest.jpg` | 4×4 labelled contact sheet from 1, 5, 9, …, 59 s |
| `delivery_evidence/frames/frame_001.0s.png` | Real Venice cold-open footage |
| `delivery_evidence/frames/frame_005.0s.png` | Kinetic title / geographic locator |
| `delivery_evidence/frames/frame_009.0s.png` | Animated lagoon/inlet map |
| `delivery_evidence/frames/frame_021.0s.png` | Foundation cross-section construction |
| `delivery_evidence/frames/frame_025.0s.png` | Pile/building animation and “MILLIONS” overlay |
| `delivery_evidence/frames/frame_033.0s.png` | 1896 archival-to-statistics beat |
| `delivery_evidence/frames/frame_037.0s.png` | Important chart animation; 300-label crowding/clipping visible |
| `delivery_evidence/frames/frame_041.0s.png` | Completed chart and label layout evidence |
| `delivery_evidence/frames/frame_045.0s.png` | MOSE gate-lift/compressed-air animation |
| `delivery_evidence/frames/frame_049.0s.png` | MOSE tide/lagoon-level animation |
| `delivery_evidence/frames/frame_053.0s.png` | Closing world map |
| `delivery_evidence/frames/frame_057.0s.png` | World comparison labels and closing typography |
| `delivery_evidence/frames/frame_059.0s.png` | Final frame treatment |

Additional extracted frames: `frame_013.0s.png`, `frame_017.0s.png`, and `frame_029.0s.png` in the same folder.

### QA, metadata, and render evidence

- `delivery_evidence/ffprobe_metadata.json.txt` — full fresh FFprobe JSON.
- `delivery_evidence/qa_summary.json` — machine-readable decode/hash/subtitle results.
- `delivery_evidence/embedded_subtitles.srt` — actual embedded subtitle extraction.
- `delivery_evidence/factual_source_review.md` — claim-by-claim source notes.
- `delivery_evidence/logs/black_freeze_decode.log` — complete decode and exact freeze timestamps.
- `delivery_evidence/logs/full_decode.log` — strict error-free decode.
- `delivery_evidence/logs/framemd5.log` — all decoded-frame hashes.
- `delivery_evidence/logs/audio_qa.log` — silence, sample statistics, EBU R128, and true peak.
- `delivery_evidence/logs/audio_boundary_analysis.json` — boundary RMS measurements.
- `delivery_evidence/logs/delivery_qa_tests.log` — twelve new media tests including one failure.
- `delivery_evidence/logs/unit_tests_with_media_tools.log` — existing suite with 45 passes and 5 skips.
- `delivery_evidence/logs/tooling_and_typescript.log` — versions and clean TypeScript result.
- `delivery_evidence/logs/render_provenance.log` — documented commands and explicit missing-log limitation.
- `delivery_evidence/logs/video_sha256.log`, `video_stat.log` — identity and size.
- `delivery_evidence/comparisons/README.txt` — v1 absence; no fabricated before/after images.

The older `examples/studio-sample-v2/editorial_contact_sheet.jpg` is preserved but was not substituted for fresh evidence.

---

## 10. Test Results

### Existing project tests — media tools supplied

```bash
PATH="$PWD/studio/remotion/node_modules/@ffmpeg-installer/linux-x64:\
$PWD/studio/remotion/node_modules/@ffprobe-installer/linux-x64:$PATH" \
  .venv/bin/python -m unittest discover -v
```

- Ran: **50**
- Passed: **45**
- Failed: **0**
- Skipped: **5**
- Result line: `OK (skipped=5)`
- Actual skip reasons: four tests require eSpeak NG in addition to media tools; `test_thumbnail_is_1280x720_jpeg...` still reported `FFmpeg/FFprobe are required` in this environment.

No source fixes were applied because there were no failures. Remaining issue: five environment-dependent tests did not execute.

### Existing project tests — without media tools on PATH

```bash
.venv/bin/python -m unittest discover -v
```

- Ran: **50**
- Passed: **40**
- Failed: **0**
- Skipped: **10**
- Result line: `OK (skipped=10)`

### New delivery media tests

```bash
python3 delivery_evidence/test_delivery_artifact.py
```

- Ran: **12**
- Passed: **11**
- Failed: **1**
- Skipped: **0**
- Failure: `test_11_no_freeze_interval_at_500ms_threshold`
- Actual error: `AssertionError: 'freeze_start:' unexpectedly found ... Static/frozen holds detected; inspect black_freeze_decode.log`.

**Fixes applied:** none to the video or working implementation, per the preserve/no-overwrite requirement. The failing result is retained rather than hidden.

### Other checks

- `npx tsc --noEmit`: **PASS**, no diagnostics.
- `delivery_evidence/run_qa.py`: completed; strict decode PASS; subtitle structure PASS; 0 exact duplicate frames.
- Factual consistency verifier: 0 internal critical findings, 2 notes for spelled-out 78 and 194. Independent source review nevertheless found the 90 cm and timber wording issues above.
- Fresh end-to-end render/rebuild: **NOT TESTED**.
- Manim/Blender adapter runtime tests: **NOT TESTED** because runtimes are absent.

---

## 11. Final Assessment

Scores are audit judgements out of 10, not automated certifications.

| Area | Score | Reasons |
|---|---:|---|
| Code implementation | **7/10** | Broad modular pipeline, validated manifests, rights/approval gates, shared fact ledger, real Remotion compositions, and useful tests. Deductions for absent optional-engine execution, non-self-contained rebuild inputs, factual gate trusting `verified` labels rather than source semantics, and QA claims that do not reproduce |
| Technical rendering | **6/10** | Valid 1080p30 H.264/AAC deliverable, clean decode, proper subtitles and strong audio headroom. Deductions for failed freeze gate, visible chart clipping, absent original render logs/intermediates, and no fresh rebuild |
| Visual quality | **5.5/10** | Real/archival footage, consistent color/type, six distinct explanatory treatments. Maps and engineering graphics remain simple/schematic, long static holds reduce pace, and 300-label clipping is a visible polish defect |
| Storytelling | **6/10** | Clear problem→geography→foundations→subsidence→MOSE→global-risk arc in 60 seconds. Deductions for compressed complexity, absolute/rhetorical wording, and limited visual variety during technical scenes |
| Audio quality | **6.5/10** | Good measured loudness/headroom, no detected long silence, ducked original score/SFX and small boundary RMS steps. No listening/ASR review means narration naturalness, intelligibility, pronunciation, music taste, and actual sync remain unverified |
| Factual accuracy | **5.5/10** | Major numbers 118, 194, 78, and 300 are traceable and narration/chart mostly agree. Serious deductions for 90 cm source mismatch and absolute timber decay/hardening claims; several broad statements need qualification |
| Automation reliability | **6/10** | Existing tests are fast and useful, TypeScript is clean, and fresh QA is reproducible. However archived v2 “zero freeze” reporting did not reproduce, 5 tests skip, no fresh render test ran, and provenance/factual checks can give false confidence without independent review |

### Release decision

**HOLD for correction and human review.** The MP4 is a valid demonstration artifact, not a factually and editorially approved final documentary.

---

## 12. Recommended Next Steps

### Critical issues

1. **Correct and re-source the chart’s 90 cm reference.** Either use the cited source’s 80 cm threshold or provide a precise authoritative definition for 90 cm. Do not merely flip the ledger’s `verified` flag.
2. **Rewrite foundation narration.** Replace “never rotted / hardened instead” with accurate wording about slow anaerobic bacterial decay and the resilient wood–water–soil system.
3. **Fix the 300-label layout.** Move/shrink the label or increase chart headroom; inspect several frames, not only the final one.
4. **Review and resolve freeze events.** Decide which holds are intentional, shorten long static periods, and make the stored QA policy consistent with fresh `freezedetect` settings.
5. **Run a complete human watch/listen and factual review before approval.** Pay particular attention to speech/subtitle alignment and claims of MOSE effectiveness.

### High-priority improvements

- Re-render v2 under a new versioned filename (for example v3), preserving v2; retain raw Remotion and FFmpeg logs and all scene outputs.
- Restore/archive v1 or remove claims of direct before/after verification; generate real paired frames when v1 is available.
- Add ASR/forced-alignment checks for narration/subtitle timing and transcript completeness; add a spelling tool with proper-noun exceptions.
- Make rebuilds reproducible by running `prepare_sample_assets.py`, recording source hashes and exact runtime versions, and checking required assets before rendering.
- Align `sample60_manifest.py` animation metadata (`animated_bars_countup`) with the actual fixed-number/bar-geometry implementation.
- Qualify “city stays dry,” “the shield works,” and “first of many,” or make their rhetorical scope explicit.
- Run all skipped media tests with a consistent modern FFmpeg/FFprobe and eSpeak NG environment.

### Optional improvements

- Add higher-quality establishing/aerial/footage coverage and more geographically accurate map detail.
- Add subtle information-bearing movement during long chart/map holds rather than motion for its own sake.
- Consider Manim for a scientifically scaled chart only if it improves clarity; consider Blender only if a genuine 3D engineering explanation is required.
- Add loudness/accessibility review, caption safe-area checks, color-contrast checks, and multiple-device playback.
- Store machine-readable environment manifests and QA thresholds alongside each versioned render.

### Tools genuinely needed

- A consistent modern **FFmpeg + FFprobe** pair for rebuilding and QA.
- Existing pinned **Python requirements** and **Remotion/npm dependencies**.
- **eSpeak NG** only if running the offline TTS integration tests or Edge TTS is unavailable.
- A spellchecker and an ASR/forced-alignment tool if subtitle/narration verification is to become a PASS rather than NOT TESTED.

### Tools that should NOT be installed yet

- **Blender:** no actual 3D shot is required for the current correction pass.
- **Manim:** the existing chart is Remotion; installing it will not fix factual or layout defects.
- Additional AI/image/video providers or API-dependent services: unnecessary for this audit and would add credentials, cost, and reproducibility concerns.
- Unpinned duplicate media frameworks or large QA stacks: use the existing focused tools until a specific uncovered requirement justifies more.

---

## Delivery Manifest

- **Main report:** `FINAL_DELIVERY_REPORT.md`
- **Evidence:** `delivery_evidence/`
- **ZIP:** `DELIVERY_BUNDLE.zip`
- **Latest MP4:** `examples/studio-sample-v2/venice_sample_60s_v2.mp4`
- The **15.99 MB MP4 is included in the ZIP** because its size is reasonable.
- No secrets, credentials, API keys, or tokens are included.
- No commit, push, deployment, source overwrite, or previous-sample deletion was performed.

### Short failure/untested summary

- **FAILED:** frozen-frame release gate (multiple static holds); one of twelve new media tests fails.
- **FAILED content review:** 90 cm does not match its cited threshold source; “timber never rotted” is too absolute; chart 300 label is visually clipped/crowded.
- **NOT TESTED:** direct v1↔v2 media comparison, fresh end-to-end rebuild, original render-process success logs, Manim/Blender rendering, narration/subtitle speech alignment, missing spoken narration via ASR, dictionary spelling, and listening-based audio quality.
- **SKIPPED:** five existing tests in the media-tool run, chiefly because eSpeak NG is unavailable.
