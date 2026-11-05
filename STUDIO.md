# GeoFactory Studio — multi-engine documentary production layer

Adds a professional production architecture on top of the existing local-first
pipeline: Remotion (motion graphics), Blender (3D), Manim (technical visuals),
FFmpeg (final assembly), all orchestrated by Python with explicit human gates.

## Stage 1 — architectural audit (summary)

| Existing piece | Verdict | Action |
|---|---|---|
| core config/DB/jobs/transitions, approval hashing | Solid | Keep unchanged |
| research/Wikimedia ledgers, licence gates | Solid | Keep |
| TTS chunking + measured SRT + manifests | Solid | Keep |
| QA technical gates (decode, duration, ledgers) | Solid | Keep |
| old equal-slice still timings (~55 s/image) | Poor pacing | Replaced: ≤22 s beats, rotation |
| single slow Ken Burns for every still | Poor variety | Replaced: 4 alternating motions + grade |
| map scenes hard-front-loaded | Weak sync | Replaced: cold open + closing montage anchors |
| publishing client (fail-closed) | Correct boundary | Keep |
| Map/thumbnail engines (Natural Earth, scored concepts) | Good foundation | Keep; Remotion adds animated versions |

New layer (this stage set):
- `geofactory/studio/scene_manifest.py` — validated per-scene production plan
  (id, narration, span, objective, engine, animation, camera, overlays,
  transition, sound, assets, source ids). `scene_manifest.json` is the contract
  between planning and rendering.
- `geofactory/studio/visual_director.py` — AI Visual Director v1: deterministic
  rules map narration beats to engines with recorded rationale and graceful
  fallback when an engine is not installed. LLM-assisted rules can slot in
  later behind the same manifest contract.
- `geofactory/studio/design_tokens.py` — shared palette/typography/camera/
  transition/sound presets; Remotion templates use the same values.
- `geofactory/studio/editorial_qa.py` — editorial QC: overused/adjacent asset
  detection, static-wall detection (>22 s still holds), objective↔engine
  agreement, per-scene contact sheet, JSON report with hard limits noted.
- CLI: `plan JOB_ID` builds `scene_manifest.json`; `editorial-report JOB_ID`
  produces `editorial_report.json` + contact sheet.

## Stage 2 — Remotion (rendered proof in this sandbox)

`studio/remotion/` is a real Remotion project (Remotion 4, React 19, TS):

- `src/compositions/VeniceColdOpen.tsx` — globe-to-Venice zoom pinned by
  `transformOrigin`, Natural Earth 1:110m world (public domain), Italy
  highlight, pulsing location marker, kinetic headline, lower third, vignette.
- Proven here: headless-Chrome dependency chain was resolved from Debian
  packages (no root), and the composition rendered to H.264
  (`out/cold-open.mp4`, 1280×720, 8 s, 240/240 frames).

Run locally: `cd studio/remotion && npm install && npx remotion browser ensure
&& npx remotion render src/index.ts VeniceColdOpen out/cold-open.mp4`

## Stage 3/4 — Manim and Blender (adapters + scenes)

- `studio/engines/manim_adapter.py`, `studio/engines/blender_adapter.py`:
  availability detection, sandboxed scene dirs, MP4 hand-off to FFmpeg.
- `studio/manim/subsidence_graph.py` — animated relative-level graph with era
  annotations (1966 flood, pumping restriction, MOSE first raise).
- `studio/blender/mose_barriers.py` — headless 3D MOSE gate: seabed/water
  materials, hollow steel gate swinging up at the hinge, tide rise, dolly orbit.
- Both runtimes are optional and never auto-installed; run
  `python3 -m geofactory.studio.engines.blender_adapter` / `...manim_adapter`
  for tailored install instructions. In this sandbox their adapters and scenes
  are code-complete but their runtimes are intentionally not provisioned.

## Stages 5–8 status (working baseline)

- Python orchestration: manifest → engines → assembly wiring is in place;
  FFmpeg assembly gains paced/motion-varied segments from the upgraded editor.
- Editorial QA: `editorial-report` implemented; it never approves on its own.
- Full-documentary sample: the 8 s cold-open template is rendered and verified;
  chaining three+ engines in one 60 s timeline is the next milestone.

All changes preserve the human-approval and publishing-disabling boundaries.
