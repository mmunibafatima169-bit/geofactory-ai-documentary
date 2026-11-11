# Production architecture roadmap

## Target architecture

Python remains the authoritative orchestrator; Remotion is the primary motion-graphics engine; FFmpeg performs final assembly. Blender, Manim and GIS are specialized preparation/motion engines, not interchangeable decoration.

```text
Topic + editorial brief
  ↓
Source registry → claim/evidence graph → human fact review
  ↓
Argument map → narration/retention plan → timed script
  ↓
Subject-aware visual director (new geofactory/production/)
  ↓
PreproductionPlan JSON
  ├─ SceneIntent + editorial job + rationale
  ├─ AssetBrief + rights requirements
  ├─ GeographicRequirement + CRS/dataset policy
  ├─ AudioDirection + loudness/ducking policy
  └─ Engine fallback / human approval state
  ↓
Capability and readiness gates (NO silent rendering)
  ↓
Asset acquisition + geospatial/data preparation
  ├─ GIS: GeoPandas / Rasterio / PyProj / Shapely
  ├─ Scientific: Manim Community
  ├─ 3D: Blender
  ├─ Footage/stills: licensed provider adapters
  └─ Audio: approved voice + music/SFX/ambience stems
  ↓
Remotion scene graph and motion system
  ↓
FFmpeg conform / mix / subtitle mux / final assembly
  ↓
Technical + editorial + rights + human readiness gates
```

## Implemented in this phase

New files only; existing samples and working pipeline files were not overwritten.

| Module | Responsibility | Verification |
|---|---|---|
| `geofactory/production/models.py` | Typed documentary, claim, asset, GIS, audio, scene and plan contracts | Unit tests and compileall |
| `direction.py` | Subject classification, semantic visual treatments, asset briefs, repetition penalty and explicit fallback | Geography/infrastructure/disaster/economics produce different treatments |
| `research.py` | Claim-to-scene linkage, verification and source-independence gates | Missing/unknown/unverified claims tested |
| `readiness.py` | Twelve quality categories with observed values, thresholds and actions | Planning cannot falsely pass final AV tests |
| `capabilities.py` | Executable/import probes separated from render verification | Contract compiled; probes recorded externally |
| `tests/test_production_readiness.py` | Six reusable architecture tests | **56 total tests pass, 5 pre-existing media skips** |

This is an implemented **pre-production kernel**, not a completed professional renderer. It currently produces data contracts only and has no video-generation path.

## Existing modules to integrate, not replace blindly

- `agents/research_agent.py`: persist source records and evidence excerpts.
- `agents/script_agent.py`: draft against verified claims and requested word counts.
- `studio/visual_director.py`: older keyword planner; migrate callers to the new subject-aware contract after compatibility review.
- `studio/scene_manifest.py`: older renderer-facing manifest; add an explicit adapter from `PreproductionPlan` rather than maintaining divergent truth.
- `studio/asset_selector.py` and `media/asset_manager.py`: replace token-only editorial acceptance with shot-level metadata/review while preserving rights gates.
- `media/map_animation_engine.py`: retain Natural Earth caching/provenance; prepare GIS outputs through the new verified GIS stack.
- `studio/engines/*_adapter.py`: repair and generalize; current adapters do not detect the isolated Blender Python runtime or incomplete Manim env.
- `media/tts_engine.py`: integrate a licensed Piper model only after audition, or another explicitly approved voice provider.
- `media/video_editor.py`: keep FFmpeg final assembly; feed it conformed stems and scene outputs only after authorization.
- `studio/editorial_qa.py` and `quality/qa_engine.py`: merge plan/readiness findings with future rendered-output QA without treating one as the other.

## Phase roadmap

### Phase 1 — Runtime completion and contracts (current phase)

- [x] Full repository/environment inventory.
- [x] Verified GIS vector/raster operations.
- [x] Subject-aware planning and readiness contracts.
- [ ] Repair `libXrender`, Cairo/Pango native dependencies.
- [ ] Verify Blender and Manim imports/CLI without claiming render quality.
- [ ] Select and licence a Piper voice or alternative narration provider.
- [ ] Version production dependency manifests and adapter configuration.

**Exit gate:** all selected engine runtimes are detected by the orchestrator; failed probes block affected scenes; no render is required for this gate.

### Phase 2 — Editorial intelligence

- Source snapshots, publisher/date/archive fields and independent-corroboration policy.
- Claim graph with support, contradiction, uncertainty and visual-evidence requirements.
- Argument map: hook, context, causal steps, complication, payoff and open loops.
- Script lint for unsupported adjectives, causal overreach, unit consistency and name pronunciation.
- Human script/table-read approval before storyboard generation.
- Multimodal asset review metadata: shot content, framing, camera motion, temporal coverage and emotional role.

**Exit gate:** blind editorial rubric meets threshold; every factual scene resolves to verified claims and every visual has an editorial purpose.

### Phase 3 — Geographic and data production

- Dataset registry with version, hash, licence, native CRS, validity and repair history.
- Projection selection by extent/purpose; geodesic routes and disputed-boundary templates.
- Sentinel/Landsat or selected provider adapter with acquisition date, cloud policy and attribution.
- DEM ingestion, vertical datum, hillshade and explicit vertical exaggeration.
- Label placement/collision tests and small-screen legibility checks.
- Tidy-data chart pipeline with units, period, methodology, uncertainty and transformation ledger.

**Exit gate:** independent geographic/data review passes on representative datasets; no production video is implied.

### Phase 4 — Reusable visual engine library

- Remotion: responsive typography, map primitives, timelines, comparisons, diagrams, footage treatments and subject-specific design tokens.
- Blender: generic terrain, engineering cutaway, mechanism and camera schemas; no location-specific hardcoding.
- Manim: scientific constructions driven by validated data and notation.
- Explicit engine adapters using isolated interpreters and resource limits.
- Still/unit contract tests first; any rendered engine validation requires separate user approval.

**Exit gate:** representative engine capabilities are actually verified when rendering is permitted; fallback never silently counts as parity.

### Phase 5 — Narration, sound and finishing

- Voice audition, pronunciation dictionary, sentence/retake manifests and forced-alignment evaluation.
- Licensed music cue sheet, ambience map, SFX semantics and stem-based sidechain mix.
- Dialogue EQ/de-essing, noise control, EBU R128 and true-peak gates plus listening review.
- Input colour-space normalization, shot matching, scopes and a controlled show look.
- Subtitle reading speed, two-line layout, sync and embedded/sidecar equivalence.

**Exit gate:** human audio/colour/subtitle approval and measurable loudness/layout targets.

### Phase 6 — End-to-end validation, only after approval

No sample or preview is authorized now. When separately approved, validate one representative production containing geography, infrastructure, data and human-consequence beats. Measure quality against the rubric, not against software installation. Do not scale to unattended 8–15 minute production until that validation passes.

## Operational policies

1. `PreproductionPlan` is the single scene-planning truth; renderer manifests are derived artifacts.
2. Engine availability, import success, render success and professional quality are separate states.
3. Rights and attribution travel with every asset and derivative.
4. Fallbacks require explicit human acceptance and are reported as quality downgrades.
5. Human gates are mandatory for script, maps, asset selection, sound and final editorial approval.
6. No publish/deploy action belongs in the automated production path.
7. Hardware limits must inform concurrency, 3D settings, cache size and memory budgets on this host.
