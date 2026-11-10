# Venice Studio Sample v2 — rendered proof

A real 60-second 1080p30 render from the GeoFactory Studio architecture. This is
included to make the repository auditable: code quality is not inferred from a
successful build; the rendered output, contact sheet and QA reports are kept
together for inspection.

## Watch

Download or open [`venice_sample_60s_v2.mp4`](./venice_sample_60s_v2.mp4).

- 60.000 seconds
- 1920×1080, 30 fps, H.264
- AAC 48 kHz stereo
- soft `mov_text` English subtitles
- measured −15.7 LUFS integrated loudness

## What the sample demonstrates

1. Licensed real Venice footage → world-to-Venice map transition.
2. Animated lagoon/inlet geography.
3. Wooden-foundation technical cross-section.
4. Public-domain 1896 archival film → sourced statistical infographic.
5. MOSE barrier engineering demonstration.
6. World comparison map with continuously animated geographic links.
7. Original synthesized music/SFX, side-chain ducking, loudness normalisation.
8. Clause-timed subtitles and a consistent design system.

## Audit artifacts

- `scene_manifest.json` — narration/timing/objective/engine/camera/overlay plan.
- `asset_selection.json` — source URLs, creator, licence, retrieval date,
  dimensions, duration, SHA-256 and relevance score.
- `factual_report.json` — source/display consistency gate; documents why the
  old visible `241 cm` was a transient counter frame and why v2 displays only
  final sourced values.
- `editorial_report_v2.json` — decoded resolution/FPS/A-V/black/freeze/audio/
  subtitle/missing-asset/factual checks.
- `editorial_contact_sheet.jpg` — one labelled frame per scene.
- `comparison_report.json` — v1 versus v2 measured findings.
- `subtitles.srt` — source subtitle cues before MP4 mux.

## Footage rights

- **Gondolas in Venice**, Amada44, CC BY-SA 3.0, Wikimedia Commons.
- **Venise, Panorama du Grand Canal, 1896**, Alexandre Promio, public domain,
  Wikimedia Commons.

Exact source/licence URLs and hashes are in `asset_selection.json`. Source
footage is not committed (106 MB); `studio/prepare_sample_assets.py` downloads,
size-checks, probes, hashes and scores it reproducibly.

## Rebuild

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
```

Automated QA found no critical or warning findings in the final v2 render, but
this does **not** certify professional quality or factual truth. Full human
viewing, listening, source review and approval remain mandatory before release.
