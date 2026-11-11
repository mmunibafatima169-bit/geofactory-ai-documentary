# FINAL DELIVERY REPORT — VENICE SAMPLE V3

**Delivery status: TECHNICAL QA PASS; EDITORIAL APPROVAL REQUIRED**  
**Video:** `examples/studio-sample-v3/venice_sample_60s_v3.mp4`  
**SHA-256:** `7f886a9e2e339d48be90efa391658f45a2a70edb8f1c57a5c506b5f209d81ec4`  
**Final size:** 21,125,079 bytes  
**Evidence bundle:** `DELIVERY_BUNDLE_V3.zip`  
**V2 preserved:** `examples/studio-sample-v2/venice_sample_60s_v2.mp4`  
**Architecture:** Python orchestration + Remotion graphics + FFmpeg assembly; Blender and Manim were not installed. No commit, push, deployment, or publication was performed.

## 1. What changed in the actual source and render

- **Science and narration:** removed the “timber never rotted”/petrification implication. S3 now states that anaerobic bacteria still attack wood, decay is slow rather than absent, and the wood–water–soil system maintains stability. MOSE and closing narration avoid promising permanent protection.
- **Factual chart:** replaced the v2 90 cm threshold with the CEDIM-supported **80 cm** reference. The measured **194 cm** 1966 peak remains distinct from **300 cm MOSE design protection**. All displayed values remain fixed during chart animation.
- **Typography:** moved the 300 cm label clear of the bar/top crop and retained safe chart margins. The v2/v3 comparison visibly demonstrates the correction.
- **Purposeful motion:** added map tide drift and continuously staggered markers, chart datum scan/band, foundation soil-inspection scan, MOSE water-level movement, and restrained diagram camera drift. Re-rendered affected scenes until the unintended chart/foundation/MOSE holds no longer triggered the agreed detector.
- **Footage:** clean cropped gondola and 1896 derivatives replace obstructed v2 picture areas; their provenance and derivation are disclosed.
- **Narration/subtitles:** six new consistent neural narration takes, fitted scene timing, remixed audio, 20 regenerated English subtitle cues, and embedded English `mov_text` subtitles.
- **Presentation:** retained the established dark documentary palette, typography system, scene structure, transitions, and Python/Remotion/FFmpeg workflow.

Actual source diff: `delivery_evidence_v3/logs/git_diff.log`. Four tracked source files changed: `studio/assemble_sample60.py`, `studio/sample60_facts.json`, `studio/sample60_manifest.py`, and `studio/remotion/src/compositions/Sample60.tsx` (168 insertions, 59 deletions at the captured final diff). V2 and its accepted evidence/report were not overwritten.

## 2. Final media verification

| Check | Exact final result | Evidence |
|---|---|---|
| Duration/container | **60.000 s** | `ffprobe_metadata.json.txt`, `qa_summary.json` |
| Video | H.264, 1920×1080, 16:9, 30/1 fps, 1,800 frames, `yuvj420p` | Same |
| Audio | AAC-LC, 48,000 Hz, stereo, 59.998979 s stream duration | Same |
| Full audio/video decode | **PASS**, exit 0, empty error log | `logs/full_decode.log` |
| Frame hashes | 1,800 decoded; 1,800 unique; 0 consecutive exact duplicates | `qa_summary.json`, `logs/framemd5.log` |
| Black detection | **PASS**: no interval at `blackdetect=d=0.10:pix_th=0.02` | `logs/black_freeze_decode.log` |
| Freeze detection | One reviewed interval only: **2.600–3.100 s, 0.500 s** | Same |
| Audio loudness | **−16.5 LUFS integrated**, **−4.1 dBFS true peak** | `logs/audio_qa.log` |
| Subtitle sidecar | 20 cues; syntax/bounds/overlap errors 0; cues >84 characters 0 | `qa_summary.json`, `subtitles.srt` |
| Embedded subtitles | English `mov_text`; extracted word sequence exactly matches sidecar | `ffprobe_metadata.json.txt`, `embedded_subtitles.srt`, `qa_summary.json` |
| Media delivery suite | **13 tests run; OK** | `logs/delivery_qa_tests.log` |
| Base unit suite | Earlier environment run: **50 tests run; OK; 5 media-dependent skips** | `logs/unit_tests.log` |
| TypeScript | `npx tsc --noEmit`, exit 0, empty log | `logs/typescript.log` |
| Factual consistency | 4 sources, 5 claims, 0 critical findings, `approval_blocked: false` | `logs/factual_consistency.log`, sample `factual_report.json` |

The unit-suite result is reported exactly as run; the five skips are not represented as passes. The final media-specific suite separately exercises the delivered file. The factual checker emits two informational notes because 78 and 194 are spoken as words rather than digits; source scripts were manually checked for those values.

### Freeze classification

**Intentional/reviewed:** 2.600–3.100 s is a 0.500 s natural low-motion moment in the real gondola shot while the opening title is present. It is retained as footage/editorial timing, not an unrendered graphic hold.  
**Unintended:** none detected in the final file at `freezedetect=n=-50dB:d=0.50`. Earlier S2/S3/S4/S5 detections led to source motion changes and complete scene re-renders; final evidence supersedes those intermediate results.

Freeze detection is heuristic. Zero exact consecutive duplicate hashes do not alone establish editorial quality.

## 3. Rendered visual evidence

- `delivery_evidence_v3/contact_sheet_latest.jpg`: 16 frames from the final file at 1, 5, 9, …, 59 s.
- `delivery_evidence_v3/comparisons/foundation_25s_v2_v3.jpg`: corrected foundation explanation.
- `delivery_evidence_v3/comparisons/chart_37s_v2_v3.jpg`: 90→80 cm correction and safe 300 cm label.
- `delivery_evidence_v3/comparisons/chart_settled_41s_v2_v3.jpg`: settled chart comparison.
- `delivery_evidence_v3/comparisons/mose_49s_v2_v3.jpg`: MOSE water-level explanation.
- `delivery_evidence_v3/frames/`: extracted final-video frames.

These comparisons are actual decoded v2/v3 frames, not mock-ups.

## 4. Reproduction commands

```bash
# Scene render form; run for each of the six composition IDs
LD_LIBRARY_PATH=/tmp/al2023/lib npx remotion render src/index.ts SCENE \
  out/sample60_v3/SCENE.mp4 --concurrency=2 \
  --browser-executable=/tmp/chromium --log=info

# Final assembly (from repository root)
PATH=/tmp/v3-bin:$PATH .venv/bin/python studio/assemble_sample60.py \
  --scenes studio/remotion/out/sample60_v3 \
  --work studio/remotion/out/work60_v3 \
  --out examples/studio-sample-v3/venice_sample_60s_v3.mp4

# Final QA
python3 delivery_evidence_v3/test_delivery_artifact.py
.venv/bin/python delivery_evidence_v3/run_qa.py
```

Environment-specific Chromium and FFmpeg paths are disclosed, not portable installation instructions. Imageio-FFmpeg n9.0.2 supplied the modern assembly binary; Remotion’s restricted compositor binary was not used for assembly. Setup attempts, failed approaches, render logs, and final commands are retained under `delivery_evidence_v3/logs/`.

## 5. Failed checks and remaining limitations

- **NOT TESTED:** ASR/forced subtitle-to-speech alignment, dictionary spelling automation, independent listening QC, external-device/browser playback, colour-managed broadcast review, and public-domain/CC licence legal clearance.
- A temporary TV-range `yuv420p` conversion passed its compatibility probe but introduced additional threshold-level freeze detections through compression rounding. It was reverted rather than hidden. The delivered H.264 stream is valid full-range `yuvj420p`; the final test explicitly accepts either planar format and the final detector result is reported above. This intermediate failure is disclosed here.
- Wikimedia original downloads failed with `SSL_ERROR_SYSCALL`; clean derivatives were cropped from preserved v2 using its existing asset ledger. See `asset_provenance.json` and `SOURCE_REVIEW.md`.
- Edge TTS could not reach its service. Arena neural speech generated the six narration takes; cached takes were reused in assembly. No successful speech-engine use is inferred from package installation.
- Early Remotion browser download and old FFmpeg assembly failed. Their alternatives are documented; final scene rendering and assembly succeeded.
- Human approval of scientific phrasing, narrative, music balance, and footage provenance is still required. This report does not claim publication approval.

## 6. Delivery decision

The requested corrected v3 source changes and new rendered MP4 exist and pass the final technical checks listed above. The sample is ready for **human editorial review**, not represented as already approved for publication.
