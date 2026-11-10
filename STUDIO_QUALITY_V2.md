# Professional documentary quality upgrade — 60-second Venice sample v2

## Preserved architecture

Python remains the orchestrator; Remotion is primary motion graphics; optional
Manim/Blender adapters remain for scientific/3D scenes; FFmpeg performs final
assembly, audio mixing, subtitles and encoding. Core research, licensing, job,
TTS, approval-hash and release gates were not rewritten.

## Audit findings addressed

- Visual Director v1 was first-match keyword logic. It now ranks all semantic
  treatments, records score/alternatives, and penalises recent objective/engine
  repetition.
- The sample used no real footage. V2 uses two story-relevant Commons assets,
  each probed, hashed, licence-tracked, relevance-scored and duplicate-checked.
- The chart's observed `241 cm` was an intermediate 0→300 spring frame—not a
  sourced value. V2 animates bar geometry but only displays final ledger values.
- Numerical overlays previously had no shared factual contract. V2 imports the
  same `studio/sample60_facts.json` used by Python factual QA.
- Editorial QA was largely manifest-level. It now decodes the final media and
  checks streams/resolution/FPS, A/V drift, black/frozen runs, silence/clipping,
  SRT syntax/bounds/readability, missing assets and factual flags.
- Long subtitle cues are clause/word split to ≤84 characters.
- Narration scene-slot audio gains micro-fades; existing side-chain music duck,
  SFX mix and EBU R128 normalisation remain.

## 241 cm / 300 cm investigation

`241` never existed in the source ledger or JSX constants. It was a transient
rendered frame while a spring drove the MOSE bar from 0 to its final target.
The final target `300 cm` is the MOSE stated design protection level (3 m),
not a measured historical flood. V2 labels it **MOSE LIMIT / design
protection** and displays 300 throughout the bar animation. `194 cm` is the
1966 Punta della Salute datum peak. Sources are recorded in
`studio/sample60_facts.json`:

- Italian Ministry of Infrastructure and Transport / Venice Water Authority,
  *The Mose: What is it and how does it work* (3 m; 78 gates).
- CEDIM / Karlsruhe Institute of Technology, using Comune di Venezia data
  (194 cm peak, 1966).
- UNESCO World Heritage Centre (118 islands).

## Assets used in v2

- `Gondolas in Venice.webm`, Amada44, CC BY-SA 3.0, Wikimedia Commons.
- `Venise Panorama du Grand Canal 1896.webm`, Alexandre Promio, public domain,
  Wikimedia Commons.

Full URLs, dimensions, duration, retrieval date, SHA-256 and scores are in
`studio/remotion/out/asset_selection.json`.

## Install and render

```bash
python3 -m pip install -r requirements.txt
cd studio/remotion
npm install --no-audit --no-fund
npx remotion browser ensure
npx tsc --noEmit
cd ../..
python3 studio/prepare_sample_assets.py
bash studio/render_scenes.sh studio/remotion/out/sample60_v2
python3 studio/assemble_sample60.py \
  --scenes studio/remotion/out/sample60_v2 \
  --work studio/remotion/out/work60_v2 \
  --out studio/remotion/out/venice_sample_60s_v2.mp4
python3 studio/sample60_manifest.py
python3 -m unittest discover
```

Linux without system Chromium libraries may need bookworm-compatible `libnspr4`
and `libnss3`; this sandbox resolves them through the existing local `.tools`
launcher library path. Manim still needs Cairo/Pango development headers and is
not silently installed. Blender remains optional and was not needed for this
2D/2.5D sample revision.

## Actual output and comparison

- V1: `studio/remotion/out/venice_sample_60s_v1.mp4`
- V2: `studio/remotion/out/venice_sample_60s_v2.mp4`
- Scene manifest: `studio/remotion/out/scene_manifest.json`
- Editorial QA: `studio/remotion/out/editorial_report_v2.json`
- Factual QA: `studio/remotion/out/factual_report.json`
- Contact sheet: `studio/remotion/out/editorial_contact_sheet.jpg`
- Comparison: `studio/remotion/out/comparison_report.json`

Both videos are 60.000 s, 1920×1080, 30 fps, H.264/AAC with soft subtitles and
-15.7 LUFS measured integrated loudness. Using the same final decoder checks:

| Metric | V1 | V2 |
|---|---:|---:|
| freeze warnings | 5 | 0 |
| subtitle readability warnings | 3 | 0 |
| licensed real/archival footage | 0 | 2 |
| factual display gate | no | yes |
| repeated assets | 0 | 0 |
| critical findings | 0 | 0 |

Automated QA does not certify professional quality or factual truth. A full
human watch, source review, pronunciation/listening review and creative decision
remain mandatory before release.
