# Production readiness audit

**Audit date:** 2026-11-10 UTC  
**Overall decision:** **NOT READY for professional automated documentary production**  
**Phase scope:** audit, selective installation, reusable pre-production architecture and verification only  
**Rendering:** **NONE**. No sample, scene, preview or video was generated.  
**Repository actions:** no commit, push, deploy or publish; existing videos/samples were not overwritten.

## Executive assessment

The repository has a credible engineering base: Python orchestration, durable jobs, claim/source ledgers, rights-aware asset adapters, Remotion motion graphics, FFmpeg assembly, measured subtitle generation and technical/editorial QA. Previous sample renders prove that a narrow pipeline can run; they do not prove a reusable professional system.

The verified GIS stack is now operational. The new `geofactory/production/` package adds subject-aware visual intent, actionable asset/GIS/audio requirements, research coverage checks and explicit readiness gates. Blender and Manim remain blocked by native dependencies; professional satellite imagery, terrain, voice, sound and reusable visual libraries remain incomplete. Editorial automation is still heuristic and requires human judgement.

## Environment summary

- Debian 12, x86_64 KVM; CPython 3.11.2.
- 2 CPU cores, 3.8 GiB RAM, no swap, 15 GiB free after installation.
- No exposed GPU. Complex 3D and high-resolution terrain throughput is unverified and likely constrained.
- Main `.venv` passes dependency checks; Blender is isolated because of NumPy incompatibility.
- FFmpeg n9.0.2 and restricted FFprobe n7.1 work through `/tmp/v3-bin`, not default PATH.
- Remotion 4.0.542 packages aligned; TypeScript check passes; Chromium 153.0.8010.0 starts with supplied library path.
- Details: `INSTALLED_TOOLS_AND_VERSIONS.md` and raw files under `production_readiness/environment/`.

## Repository architecture audit

| Production area | Existing implementation | Actual maturity |
|---|---|---|
| Orchestration/jobs | `core/config.py`, `database.py`, `jobs.py`, CLI and worker; SQLite transitions, recovery and approval hashes | Solid foundation; not yet driven by the new plan contract |
| Research | Wikimedia API discovery, imported source/claim ledgers, evidence excerpts and review status | Traceable but limited discovery; no primary-source orchestration or contradiction graph |
| Scriptwriting | Source-aware local notes, optional Groq/Ollama drafts and claim-ID/word-count checks | Evidence-aware draft support, not benchmark-level storytelling |
| Scene planning | `studio/visual_director.py`, `scene_manifest.py`; keyword rules, fallbacks and camera fields | Useful v1; topic bias and template repetition remain |
| **New visual direction** | `production/direction.py` and typed models | Subject-aware scene intents and explicit downgrade records; tested without rendering |
| Asset acquisition | Commons images, official Pexels/Pixabay video, local music, rights/hashes | Rights architecture stronger than cinematic relevance; live provider search not tested |
| Asset selection | Token overlap, technical scoring and duplicate-frame signatures | Cannot understand actual shot semantics, composition or emotion |
| GIS/maps | Natural Earth 110m/50m country layers, zoom/highlight and explicit coordinates | Basic maps; now supported by working GIS libraries, but no professional imagery/terrain/label pipeline |
| 2D/motion | Remotion compositions, Pillow/SVG graphics and FFmpeg transforms | Engine proven; reusable professional component coverage limited |
| 3D | One Blender adapter and one subject-specific script | Runtime blocked; no generic production capability |
| Scientific | One Manim adapter and one subject-specific graph | Runtime not installed; no generic capability |
| Narration | Edge/eSpeak/Piper code paths, chunk decode checks and measured SRT | Piper imports but has no voice; no verified natural narration provider |
| Audio | Local licensed music, basic mix and QA measurements | No stem-based sound design, verified ducking or listening standard |
| Editing/assembly | FFmpeg timeline, H.264/AAC, soft SRT and loudness checks | Functional final assembler; limited compositing/colour workflow |
| QA | Technical, factual, rights, editorial and approval gates | Strong base; visual quality, sync, listening and geographic review still need human checks |
| Publishing | Intentionally disabled/fail-closed | Appropriate for current readiness |

Full inventory: `production_readiness/environment/repository_inventory.txt`.

## Installation verification summary

| Capability | Evidence-based state |
|---|---|
| Python/Remotion/FFmpeg | Existing evidence retained; no unnecessary reinstall |
| GIS vector/raster | **PASS** for actual vector read/reprojection and in-memory raster write/read |
| Geometry quality | **WARNING:** 2 of 177 existing Natural Earth geometries invalid |
| Blender | **FAIL runtime:** installed `bpy` 4.5.16 cannot import without `libXrender.so.1` |
| Manim | **NOT INSTALLED:** native Cairo/Pango/pkg-config blocker |
| Piper | **PARTIAL:** package import works; no voice model or synthesis verification |
| ImageMagick | **PASS:** existing v6 runtime |
| QGIS/GDAL CLI | **ABSENT:** not needed for current headless wheel-based GIS route |
| Satellite provider | **MISSING** |
| Image generation | **MISSING** |

See `MISSING_TOOLS_AND_INSTALLATION_STATUS.md` for exact blockers/manual steps.

## Professional quality-readiness checklist

Statuses apply to the **system**, not to a newly rendered film. “MET” here means a measurable planning/foundation requirement only. Any final film would require separate rendered-output QA and human approval.

| Category | Measurable readiness requirement | Current observation | Status |
|---|---|---|---|
| Storytelling & narration | Central question, causal outline, hook/payoff, table-read approval; 100% factual sentences claim-linked | Typed profile and scene links implemented; no evaluated argument map, table read or natural voice | **PARTIAL** |
| Visual relevance & quality | Every scene has an editorial job and claim-linked asset brief; 100% selected shots human-reviewed | Briefs generated; no multimodal selection or shot review | **PARTIAL** |
| Maps & geographic accuracy | Versioned dataset, hash, valid geometry, native/display CRS, dispute policy and geographic approval for every spatial layer | GIS transforms work; contracts added; existing data has 2 invalid geometries; no complete production workflow | **PARTIAL** |
| Animation & motion design | Every selected engine runtime-verified; no unapproved downgrade; reusable motion primitives | Remotion verified previously; Blender/Manim blocked; new fallback is explicit | **MISSING** |
| Cinematic footage | Exact place/process match, >=1920×1080 target, stable/usable motion, no unexplained repetition, 100% human shot review | Provider adapters exist; no curated library or visual shot review | **MISSING** |
| Infographics & typography | Units/source on every chart, fixed verified values, safe areas, no collision/clipping at target/small-screen sizes | Some components/QA exist; no complete chart grammar or reusable fit tests | **PARTIAL** |
| Editing & transitions | Continuous timeline, motivated transitions, no broken media, full human continuity review | FFmpeg assembler exists; no visual timeline editor or professional transition evaluation | **PARTIAL** |
| Audio & sound design | Approved voice, pronunciation checks, synced stems, sidechain ducking, −16 LUFS-I, ≤−1.5 dBTP, listening approval | Measurement possible; premium voice/music/ambience workflow absent | **MISSING** |
| Colour consistency | Declared input spaces, shot matching, scopes, show look and representative display review | Basic grade/palette only | **MISSING** |
| Pacing & retention | Planning heuristic scenes ≤18s where appropriate, information-density review, hook/open-loop/payoff audit | New readiness metric exists; no retention editorial evaluation | **PARTIAL** |
| Factual accuracy | 0 unknown/unverified/unsourced scene claims; independent source count recorded; contradiction review | Claim checks implemented and tested; no broad primary-source/contradiction system | **PARTIAL** |
| Asset provenance & licensing | Source/creator/licence/attribution/hash for every asset and derivative; 100% rights approval | Strong existing gates; no production-wide verified asset corpus | **PARTIAL** |

**Readiness result:** 0 categories establish full professional readiness; 8 partial foundations and 4 missing production capabilities. This is not a numerical quality score and must not be converted into a publication claim.

## Automated verification performed

- **56 tests run, OK; 5 pre-existing media-dependent skips.** Six new architecture tests cover subject variation, explicit fallback, research gates, readiness limits, runtime validation and subject classification.
- Main and isolated Blender environment `pip check`: no broken requirements.
- Python compile check for new modules: passed.
- Remotion package alignment and TypeScript check: passed.
- GIS vector read/reprojection: passed, with invalid geometry warning.
- Raster in-memory GeoTIFF round trip: passed.
- Blender import: failed as documented.
- Manim import: failed because installation is incomplete.
- Piper import/help: passed; synthesis **NOT TESTED**.
- No video render, audio sample generation or preview was performed.

Raw logs: `production_readiness/verification/`.

## Remaining blockers

### Hard environment blockers

1. Debian repository network access prevents installation of `libXrender`, Cairo/Pango development packages and related native dependencies.
2. Blender standalone CLI is absent; installed Python wheel is not detected by the existing CLI adapter.
3. No Piper voice model; no verified natural local narration.
4. Hardware has no exposed GPU and only 2 cores/3.8 GiB RAM for professional 3D workloads.

### Architecture and quality blockers

1. No satellite/aerial provider, DEM/terrain workflow or professional cartographic label system.
2. No reusable Blender/Manim component libraries or verified engine adapters.
3. No primary-source research graph, contradiction handling or story-retention model.
4. Asset selection lacks visual/multimodal understanding and human-reviewed shot metadata.
5. No professional narration, stem-based sound design, colour management or forced subtitle alignment verification.
6. New pre-production contracts are not yet connected to the older CLI/job/render manifest flow.
7. Existing GIS data contains invalid geometries requiring explicit repair/review.
8. Human editorial, geographic, rights, listening and visual approvals are not replaceable by installation or unit tests.

## Phase completion decision

The requested audit and reusable architecture phase is complete to the extent permitted by the environment. **Do not begin video generation.** Repair native dependencies and implement the next roadmap phase only after user approval. See `PRODUCTION_ARCHITECTURE_ROADMAP.md` for ordered work and exit gates.
