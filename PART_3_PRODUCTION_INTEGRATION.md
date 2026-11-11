# Phase 2 — Part 3: Audio and reusable production integration

**Date:** 2026-11-11 UTC  
**Result:** audio engine and cross-domain gates implemented; Piper quality and blocked visual runtimes remain unresolved  
**Video generation/rendering/previews:** none  
**Audio verification:** short synthetic audio-only WAV signals and a 4-second stereo mix  
**Commit, push, deployment or publishing:** none

## 1. Piper voice quality, pronunciation and consistency

**Status: NOT VERIFIED / BLOCKED.**

Piper 1.8.0 still imports, but no English ONNX voice model is available because Part 1 documented the model-host network restrictions. Therefore:

- no Piper speech was synthesized in this phase;
- pronunciation was not tested;
- naturalness and speaker consistency were not auditioned;
- no voice-quality approval is claimed.

New `geofactory/production/narration.py` provides the reusable path once a licensed model is available:

- loads a specified ONNX model and JSON configuration through `PiperVoice`;
- synthesizes mono speech chunks only, with scene/chunk linkage;
- records text, audio and model hashes, measured duration, sample rate and channels;
- binds `VoiceQualityReview` to the exact model hash;
- requires named human approval for pronunciation, consistency and naturalness;
- rejects inconsistent PCM formats and model/review mismatches.

This avoids treating successful synthesis as proof of editorial voice quality.

## 2. Reusable narration and audio processing

### Narration

The new manifest complements the existing `media/tts_engine.py` sentence chunking, decode checks and measured SRT workflow. It adds model reproducibility and human quality gates without replacing the existing working code.

### Audio mixing

New `geofactory/production/audio.py` implements:

- scene-linked narration, music, ambience and SFX cues;
- gain, trim and start-time controls;
- one concatenated narration input as the dialogue sidechain key;
- independent key branches for music and ambience;
- 8:1 music and 4:1 ambience compression with 20 ms attack/400 ms release;
- SFX delay/placement without decorative automatic impacts;
- 48 kHz stereo PCM24 audio-only output;
- −16 LUFS target, −1.5 dBTP loudnorm ceiling and final limiting/resampling;
- rejection of video containers in the audio-only mixer;
- structured command, cue and sound manifests.

### Actual audio-only verification

Four synthetic WAV stems were mixed through the real FFmpeg n9.0.2 binary. No video stream or preview was created.

| Measurement | Result |
|---|---|
| Output | 48,000 Hz, stereo, 4.000 s |
| Integrated loudness | **−16.5 LUFS** |
| True peak | **−11.7 dBFS** |
| 110 Hz music RMS before narration | 0.099581 |
| 110 Hz music RMS during narration | 0.027213 |
| 110 Hz music RMS after recovery | 0.086019 |
| Active/quiet ducking ratio | 0.273279 |
| Measured music ducking | **−11.27 dB** |
| Finite PCM samples | yes |

The frequency-isolated measurement verifies actual dialogue-keyed music attenuation and recovery, rather than merely checking that a `sidechaincompress` string exists. This synthetic engineering test is not a music-mix listening approval.

Evidence:

- `production_readiness/part3/logs/audio_mix_verification.txt`
- `logs/audio_pcm_analysis.txt`
- `logs/audio_loudness.txt`
- `logs/ducking_measurement.txt`
- `audio/sound_manifest.json`

A PCM24 WAV initially caused Python's basic `wave` reader to report unknown format 65534 (WAV extensible). SoundFile read it successfully; this reader limitation is retained in the logs and was not misreported as an FFmpeg failure.

## 3. Licensing-safe music and SFX sourcing

`SoundAsset` requires:

- explicit role and local audio file;
- source and licence HTTPS URLs;
- creator and attribution;
- SHA-256 file integrity;
- an approved reuse-licence allowlist entry;
- explicit `rights_approved=true`.

Unknown licences, missing attribution, unapproved rights, missing files and hash mismatches fail closed. Music, ambience and SFX all follow the same provenance contract. The manifest warns that an allowlist is not legal clearance.

Existing owner-downloaded music registration remains intact. The new layer connects those approved assets to scene cues rather than scraping music or assuming that “royalty free” means unrestricted commercial use.

## 4. Visual/runtime production integration

`engine_adapters.py` now has a common non-rendering capability registry for:

- Blender;
- Manim;
- GIS;
- FFmpeg and FFprobe;
- Remotion package/version alignment.

Actual current registry result:

| Capability | Runtime state |
|---|---|
| GIS 1.2.0 | verified import |
| FFmpeg n9.0.2 | verified version |
| FFprobe n7.1 | verified version/probe |
| Remotion 4.0.542 | verified aligned packages |
| Blender | installed, runtime blocked by `libXrender.so.1` |
| Manim | not installed |

The registry connects with Part 2's `plan_preparation`, typed GIS/satellite/DEM jobs and Blender/Manim scene configurations. It does not mark an engine executable from source code alone. Blender, Manim, live satellite acquisition and terrain appearance remain unverified.

Evidence: `logs/capability_registry.txt`.

## 5. Topic-aware planning with common standards

New `quality_standards.py` defines common minimums for all subjects:

- maximum scene duration and common timeline validity;
- claim and asset-brief linkage for every scene;
- audio direction for every scene;
- 1920×1080 minimum planning target;
- 48 kHz audio, −16 LUFS and −1.5 dBTP targets;
- visual-monotony detection for longer plans.

Subject policies distinguish appropriate techniques:

- **Geography:** GIS maps, satellite context, routes, footage and charts.
- **Infrastructure:** engineering cutaways, mechanisms, terrain, footage and data.
- **Disasters:** hazard sequences, timelines, satellite/archival evidence and footage.
- **Economics:** charts, economic flows, comparisons, geographic context and footage.

These policies share factual, rights, pacing and audio standards without forcing every topic into the same visual template. A technique outside a subject's normal policy produces an editorial-review finding, not silent acceptance.

## 6. Stronger production readiness gates

New `gates.py` detects:

- unprobed or unavailable preparation/motion engines;
- missing Remotion or FFmpeg;
- unresolved asset briefs and unapproved rights;
- unapproved engine downgrades;
- unassigned GIS datasets/CRS;
- unverified live satellite acquisition;
- unverified terrain runtime;
- missing or invalid scene-linked audio mixes;
- missing human voice-quality approval;
- missing claims, asset briefs, audio direction and visual monotony.

The gate result always keeps `video_render_authorized=false`; it is a planning/readiness system, not permission to render.

## 7. Complete test evidence

```text
Ran 70 tests in 8.171s
OK (skipped=5)
```

Five new Part 3 tests cover:

1. Independent music/ambience sidechain keys and loudness graph.
2. Licensing-rights rejection.
3. Model-bound, human-gated narration review.
4. Shared standards with different subject treatments.
5. Tool/asset/voice/satellite readiness blockers.

Additional evidence includes the real FFmpeg mix and ducking measurements, common capability probes, compilation checks, clean `pip check`, and unchanged sample hashes.

## Remaining blockers

1. Piper English model, pronunciation, naturalness and consistency remain unverified.
2. Blender and Manim are still not operational; Part 1 native/network repair is required.
3. Live satellite acquisition and real DEM/terrain visual quality remain untested.
4. No production music/SFX library has received editorial and legal review.
5. The synthetic mix does not establish professional narration, musical taste or final listening quality.
6. No production plan has satisfied all asset, source, tool and human gates; system remains NOT READY.

**Stop after Part 3. No video generation has been started or authorized.**
