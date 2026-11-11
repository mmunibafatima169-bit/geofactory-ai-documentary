# Phase 2 — Part 1: Software verification

**Date:** 2026-11-11 UTC  
**Overall result:** **INCOMPLETE — native/network blockers remain**  
**Video rendering:** none  
**Audio speech generated:** none; Piper model download failed  
**Repository preservation:** existing source files, samples and working environments were not overwritten. No commit, push or deployment.

## Task results

| Requested task | Result | Actual evidence |
|---|---|---|
| Fix Blender `libXrender.so.1` failure | **BLOCKED** | Debian repositories and `download.blender.org` unreachable; `bpy` still fails import |
| Complete Manim/Cairo/Pango setup | **BLOCKED** | Same native repository blocker; Manim remains uninstalled |
| Install suitable Piper English voice | **BLOCKED** | Hugging Face and GitHub release-asset/CDN connections fail |
| Verify actual Blender launch | **FAILED / NOT VERIFIED** | `blender`: exit 127; `import bpy`: exit 1 |
| Verify actual Manim execution | **FAILED / NOT VERIFIED** | `.venv-manim/bin/manim`: absent, exit 127 |
| Verify Piper speech synthesis | **FAILED / NOT VERIFIED** | No model; synthesis exits 1; no WAV produced |
| Python/Node/Remotion/FFmpeg compatibility | **PASS for non-rendering checks** | Versions, dependency checks, tests and runtime probes below |

Logs: `production_readiness/part1/logs/`. This phase does not claim the three blocked capabilities work.

## Environment and compatibility baseline

- Debian GNU/Linux 12, x86_64; 2 CPU cores; 3.8 GiB RAM; no swap.
- 15 GiB free at baseline; sufficient for the attempted native packages and approximately 63.2 MB Piper model.
- No exposed GPU; Piper was intended for CPU inference.
- Python 3.11.2 remains appropriate for the installed packages.
- Blender was already isolated in `.venv-blender` because its NumPy `<2` requirement conflicts with the main GIS environment. That environment was preserved.
- Manim remains isolated in `.venv-manim`; no working package was replaced.

## Verified working tools

| Tool | Exact version | Commands/checks | Result |
|---|---|---|---|
| System/main Python | CPython 3.11.2 | `python3 -VV`, `.venv/bin/python -VV` | PASS |
| Main environment dependencies | See Phase 1 frozen manifest | `.venv/bin/pip check` | PASS: no broken requirements |
| Blender isolated dependencies | `bpy` package 4.5.16 remains present | `.venv-blender/bin/pip check` | PASS for package consistency only; runtime still fails |
| Manim isolated environment | Empty/incomplete | `.venv-manim/bin/pip check` | PASS only for the empty environment; not Manim verification |
| Python test suite | Existing + architecture tests | `PATH=/tmp/v3-bin:$PATH .venv/bin/python -m unittest discover -v` | **56 run, OK, 5 pre-existing media skips** |
| Node.js | 22.22.3 | `node --version` | PASS |
| npm | 10.9.8 | `npm --version` | PASS |
| Remotion | 4.0.542 | `npx remotion versions` | PASS: all Remotion packages aligned |
| React / React DOM | 19.3.1 / 19.3.1 | `npm list ... --depth=0` | Installed and dependency tree readable |
| TypeScript | 5.9.3 | `npx tsc --noEmit` | PASS |
| FFmpeg | n9.0.2-17-g2a571b6068-20260930 | `/tmp/v3-bin/ffmpeg -version` | PASS |
| FFprobe | n7.1, Remotion restricted build | `/tmp/v3-bin/ffprobe -version` | PASS for probing; not a full FFmpeg replacement |
| Chromium | 153.0.8010.0 | `LD_LIBRARY_PATH=/tmp/al2023/lib /tmp/chromium --version` | PASS |

FFmpeg filter inventory confirmed `loudnorm`, `ebur128`, `aresample`, `rubberband`, `sidechaincompress`, `ass`, `subtitles` and `xfade`. No video filter was executed. FFmpeg and FFprobe versions differ because they come from different builds; existing non-rendering probes work, but this phase does not claim a newly rendered compatibility test.

Raw compatibility logs:

- `production_readiness/part1/logs/compatibility_python_node.txt`
- `production_readiness/part1/logs/compatibility_media.txt`

## Blender blocker — exact state

Existing `.venv-blender` contains `bpy` 4.5.16. Actual commands:

```text
$ blender --version
/bin/bash: blender: command not found
exit=127

$ .venv-blender/bin/python -c 'import bpy; print(bpy.app.version_string)'
ImportError: libXrender.so.1: cannot open shared object file: No such file or directory
exit=1
```

The existing repository adapter also returns `BlenderStatus(available=False)` because no standalone `blender` executable is on PATH. A `bpy` wheel is not a substitute for that adapter's CLI requirement.

### Network evidence

`sudo -n apt-get update` cannot connect to `deb.debian.org` on port 80. Direct HTTPS probes to `deb.debian.org` and `download.blender.org` end with `OpenSSL SSL_connect: SSL_ERROR_SYSCALL`. No unverified third-party binary library was installed as a workaround.

Logs:

- `logs/apt_update_retry.txt`
- `logs/direct_native_download_probe.txt`
- `logs/required_execution_attempts.txt`

### Manual repair when Debian access is permitted

```bash
sudo apt-get update
sudo apt-get install -y libxrender1

# Verify the existing Python runtime without rendering:
.venv-blender/bin/python -c \
  'import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); print(bpy.app.version_string)'

# The existing CLI adapter additionally needs the official Blender executable:
# Install a supported official Blender 4.5 LTS distribution and add it to PATH.
blender --version
blender -b --factory-startup --python-expr \
  'import bpy; print("Blender background launch OK", bpy.app.version_string)'
```

The background launch command initializes Blender only; it has no render operator or output video.

## Manim blocker — exact state

Phase 1 installation failed because PyCairo/ManimPango could not find `pkg-config`, Cairo and Pango development dependencies. The same Debian network blocker remains.

```text
$ .venv-manim/bin/manim --version
/bin/bash: .venv-manim/bin/manim: No such file or directory
exit=127

$ .venv-manim/bin/python -c 'import manim'
ModuleNotFoundError: No module named 'manim'
```

### Manual repair when Debian access is permitted

```bash
sudo apt-get update
sudo apt-get install -y pkg-config libcairo2-dev libpango1.0-dev
.venv-manim/bin/pip install manim==0.22.1
.venv-manim/bin/manim --version
.venv-manim/bin/python -c \
  'import manim; s=manim.Scene(); print("Manim execution OK", manim.__version__, type(s).__name__)'
```

This verifies import and scene-object execution without calling `Scene.render()` or producing a video.

## Piper voice blocker — exact state

Piper 1.8.0 itself imports and its CLI help works. The selected voice was **en_US-lessac-medium**, single-speaker US English, 22,050 Hz, approximately 63.2 MB. It is a reasonable CPU voice candidate, but its editorial quality could not be auditioned.

Official attempt:

```bash
.venv/bin/python -m piper.download_voices \
  --data-dir production_readiness/part1/voices en_US-lessac-medium
```

Result: `URLError: TLS/SSL connection has been closed (EOF)`, exit 1.

A permitted GitHub mirror was identified:

```text
https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/
vits-piper-en_US-lessac-medium.tar.bz2
```

Both the normal release URL and GitHub API asset endpoint redirect to blocked binary hosts (`release-assets.githubusercontent.com`), ending in `SSL_ERROR_SYSCALL`. GitHub repository alternatives were inspected; the located model blobs use Git LFS and require another blocked media host. No model was installed from an unverifiable source.

Actual synthesis attempt:

```text
ValueError: Unable to find voice: production_readiness/part1/voices/en_US-lessac-medium.onnx
exit=1
```

No `piper_verification.wav` exists.

### Manual installation and verification when model-host access is permitted

```bash
.venv/bin/python -m piper.download_voices \
  --data-dir production_readiness/part1/voices en_US-lessac-medium

printf 'This is a software verification narration test.' | \
  .venv/bin/python -m piper \
    -m production_readiness/part1/voices/en_US-lessac-medium.onnx \
    -f production_readiness/part1/piper_verification.wav

/tmp/v3-bin/ffprobe -v error \
  -show_entries stream=codec_name,sample_rate,channels:format=duration \
  -of json production_readiness/part1/piper_verification.wav
```

The WAV must then be checked for non-silence and auditioned for pronunciation, pacing and naturalness. Download alone is not a successful speech-quality verification.

Logs:

- `logs/piper_official_download_attempt.txt`
- `logs/piper_voice_download.txt`
- `logs/piper_voice_api_download.txt`
- `logs/github_voice_code_search.json`
- `logs/required_execution_attempts.txt`

## Part 1 decision

**Part 1 acceptance is not met.** Python, Node.js, Remotion, Chromium and FFmpeg remain compatible under the performed non-rendering checks. Blender, Manim and Piper speech cannot be marked operational until the network/native blockers are repaired and the actual verification commands above succeed.

Stop here. Part 2 has not been started.
