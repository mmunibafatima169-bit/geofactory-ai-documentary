# Professional quality gap analysis

Benchmark: the storytelling, geographic clarity, pacing and polish associated with high-quality channels such as RealLifeLore. This is a quality reference only; no scripts, branding, thumbnails or copyrighted assets are copied.

**Current conclusion: substantial engineering foundations, but not yet a professional automated documentary system.** The largest gap is no longer FFmpeg/Remotion availability; it is repeatable editorial intelligence, source-to-visual evidence, premium asset supply, finished GIS/3D/scientific pipelines and human-calibrated sound/pacing.

## A. Cinematic visual production

| Capability | Current evidence | Gap to benchmark | Rating |
|---|---|---|---|
| Relevant real-world footage | Commons/Pexels/Pixabay adapters, rights records and relevance scoring exist | Token overlap cannot judge shot content, composition, movement or emotional relevance; no live curated footage library or shot-level review | **PARTIAL** |
| Satellite/aerial imagery | Scene objective and new asset brief can request it | No provider integration, acquisition-date workflow, cloud handling, map attribution, raster compositing or imagery cache | **MISSING** |
| Cinematic camera movement | FFmpeg still movement and Remotion camera/drift patterns exist | Limited virtual moves; no footage-aware reframing, depth/parallax, stabilization or verified 3D camera system | **PARTIAL** |
| Custom maps/geographic transitions | Natural Earth country zoom/highlight, markers/routes and Remotion map graphics | Generalized 1:110m/1:50m data, limited projections/layers; no robust route geodesics, detailed relief, label collision engine or satellite workflow | **PARTIAL** |
| Motion graphics/typography | Remotion is proven by prior sample; theme tokens and QA exist | Only limited compositions; no reusable layout system with measured type fitting, modular lower thirds, templates per subject or full visual review suite | **PARTIAL** |
| 2D animation | Remotion and Pillow/SVG available | Existing rules often reduce varied topics to charts/maps; new planner improves intent but has no rendered component library yet | **PARTIAL** |
| 3D animation | One subject-specific Blender script and CLI adapter exist | Blender runtime blocked; no generic scene schema, materials, lighting, terrain import, camera library or asset pipeline | **MISSING** |
| Engineering/scientific visualization | Scene manifest supports engineering; one Manim graph and one MOSE script | Both are subject-specific; Manim not operational; no dimensional validation, schematic-versus-real labelling or reusable mechanism primitives | **MISSING** |
| Data charts/infographics | Remotion charts, basic SVG chart, factual number checks | No tidy-data transformation ledger, units methodology, uncertainty, axis/zero-baseline policy or reusable chart grammar | **PARTIAL** |
| Transitions/visual storytelling | Cuts/dissolves/wipes and editorial timing fields | Transition selection is rule-based rather than motivated by spatial/narrative continuity; no timeline visual editor | **PARTIAL** |

## B. Geographic production

**Now verified:** GeoPandas vector reading, CRS reprojection, PyProj transforms and Rasterio in-memory GeoTIFF I/O. This is meaningful progress, not professional map output by itself.

Remaining gaps:

1. **Geometry QA:** the existing 177-feature Natural Earth file has 2 invalid geometries. Production must validate/repair with a logged method rather than silently rendering them.
2. **CRS and scale:** new contracts require native/display CRS, but the existing older map engine is Pillow-based and does not provide a complete cartographic projection pipeline.
3. **Data depth:** Natural Earth is suitable for global/regional context, not city infrastructure, detailed coastlines or engineering-scale geography.
4. **Relief and terrain:** no DEM ingestion, vertical datum policy, hillshade, tiling, LOD or Blender terrain builder.
5. **Imagery:** no Sentinel/Landsat/commercial provider integration, acquisition metadata or attribution enforcement.
6. **Labels/routes:** no collision-aware place labels, geodesic routes, disputed-border presentation test or map-review UI.
7. **QGIS:** optional for human cartographic work, not a substitute for automated GIS correctness.

**Geographic rating: PARTIAL for basic vector/raster processing; MISSING for professional end-to-end geographic visualization.**

## C. Editing and sound

| Area | Current state | Professional gap |
|---|---|---|
| Timeline/compositing | Programmatic FFmpeg timeline and Remotion composition; hash-bound approval | No reusable multi-track scene graph, visual timeline editor, nested comps, adjustment layers or per-shot colour pipeline |
| Narration | Chunked TTS, FFprobe checks and measured SRT; Piper package now imports | No voice model audition, pronunciation dictionary, emotional direction, de-essing, breath control or human listening approval |
| Music/SFX/ambience | Rights-aware local music and basic volume mixing | No cue sheet, stem management, scene-aware score selection, authentic ambience library or verified sidechain-ducking engine |
| Loudness | QA can measure peaks and previous sample used EBU R128 | Loudness measurement is not a complete mix; dialogue consistency, true peak and listening devices need human QC |
| Colour | Basic FFmpeg grading and consistent Remotion palette | No input colour-space normalization, shot matching, scopes-driven grade, skin-tone policy or managed show LUT |
| Subtitles | Measured chunk timings and SRT validation | Sentence weighting is not forced alignment; no ASR alignment verification, reading-speed/full-two-line parser in every path or human sync review |

**Editing/sound rating: PARTIAL technically; MISSING verified premium narration and sound design.**

## D. Documentary intelligence

### Existing strengths

- Source and claim ledgers, human-review status, supported-number checks and approval gates.
- Source-aware script notes with optional Groq/Ollama drafting; model output is not treated as evidence.
- Job persistence, recovery, approval hashing and fail-closed publishing.
- Editorial heuristics for repeated assets, static walls, scene objectives and subtitle bounds.

### New reusable improvements in this phase

`geofactory/production/` now adds:

- Subject profiles for geography, infrastructure, disaster and economics.
- Scene intents that distinguish editorial job, visual technique, preparation engine and motion engine.
- Actionable asset briefs and geographic CRS/dataset requirements.
- Explicit `QUALITY DOWNGRADE` records when a selected engine is unavailable.
- Claim-to-scene coverage checks and measurable readiness results.
- Non-rendering capability probes that never claim render success.

### Remaining intelligence gaps

- Deterministic keyword classification is only a baseline; it cannot reliably understand causality, narrative tension, irony, ambiguity or retention.
- No research orchestration across primary documents, datasets and independent corroboration with archived snapshots.
- No argument map, hook/payoff structure, open-loop tracking, contradiction detection or spoiler/pacing plan.
- No multimodal asset understanding; tags are not enough for cinematic selection.
- No learned/evaluated decision set showing when a map, footage, chart or 3D scene improves comprehension.
- No benchmark corpus or blind human review process for script and storyboard quality.

**Documentary intelligence rating: PARTIAL for evidence-aware scaffolding; MISSING demonstrated benchmark-level autonomous editorial judgement.**

## Priority order

1. Repair Blender/Manim runtimes and implement non-Venice engine adapters.
2. Build a real source→claim→script→storyboard→asset data flow with human approvals.
3. Build GIS imagery/DEM/route/projection pipelines and geometry QA.
4. Establish voice, music, ambience and colour benchmarks through human listening/viewing.
5. Expand reusable Remotion components and subject-specific design systems.
6. Only after readiness approval, use separately authorized non-video unit scenes and eventually a full production validation. This phase performs neither.
