# Installed tools and versions

Audit date: **2026-11-10 UTC**. This distinguishes an installed package from a working runtime. No video was generated or rendered during this audit. Raw evidence is under `production_readiness/`.

## Host and runtime

| Item | Observed value | Verification |
|---|---|---|
| OS | Debian GNU/Linux 12 (bookworm), x86_64, kernel 6.1.158+ KVM guest | `environment/system.txt` |
| CPU | 2 logical Intel Xeon CPUs @ 2.60 GHz; AVX2/AVX-512 available | Same |
| RAM | 3.8 GiB total, 3.5 GiB available at probe; no swap | Same |
| Storage | 21 GiB root filesystem; **15 GiB free after installs** | `environment/final_state.txt` |
| GPU | No NVIDIA utility, `/dev/dri`, or exposed display GPU found | `environment/system.txt` |
| System Python | `/usr/bin/python3`, CPython 3.11.2; not a venv | `environment/runtimes.txt` |
| Main project environment | `.venv/bin/python`, CPython 3.11.2; pip 23.0.1 | Same |
| Node.js / npm / npx | 22.22.3 / 10.9.8 / 10.9.8 | Same |
| Main dependency health | `pip check`: no broken requirements | `verification/tests_after_architecture.txt` |

## Working media and graphics tools

| Tool | Version / path | What was actually verified |
|---|---|---|
| FFmpeg | n9.0.2 (2026-09-30 build), `/tmp/v3-bin/ffmpeg` | Version and compiled capabilities. It includes x264/x265, libass, libsoxr and librubberband. Not installed on default PATH. |
| FFprobe | n7.1, `/tmp/v3-bin/ffprobe` (Remotion build) | Version/probe capability; restricted Remotion build. Not default PATH. |
| Remotion | 4.0.542; all Remotion packages aligned | `npx remotion versions`; TypeScript `npx tsc --noEmit` passed. Prior v3 render evidence exists separately; no new render performed. |
| React / React DOM | 19.3.1 / 19.3.1 | Installed package inventory. |
| TypeScript | 5.9.3 | Compile check passed. |
| Chromium | 153.0.8010.0, `/tmp/chromium` | Version worked with `LD_LIBRARY_PATH=/tmp/al2023/lib`. No system browser on PATH. |
| Pillow | 13.0.0 | Installed and exercised by existing tests. |
| ImageMagick | 6.9.11-60 Q16 (`convert`, `identify`) | Version/runtime probe passed. ImageMagick 7 `magick` command absent; equivalent v6 commands available. |
| PyAV | 18.1.0 | Installed package; no new media render performed. |
| imageio-ffmpeg | 0.8.1 | Installed and supplies the n9.0.2 binary. |

## GIS and data stack — runtime verified without rendering video

| Package | Version | Verification |
|---|---|---|
| GeoPandas | 1.2.0 | Read 177 features from existing Natural Earth GeoJSON and reprojected to EPSG:3857. |
| Shapely | 2.2.0 | Geometry validation ran: **175/177 valid; 2 invalid**. This is a data-quality issue, not a silent pass. |
| PyProj / PROJ | 3.7.2 / 9.5.1 | EPSG:4326→3857 transform returned expected coordinate values. |
| Rasterio / bundled GDAL | 1.4.4 / 3.10.3 | In-memory 4×4 GeoTIFF write/read round trip passed; no video output. |
| Fiona / bundled GDAL | 1.10.1 / 3.9.2 | Import/version probe passed. Note that Fiona and Rasterio bundle different GDAL versions. |
| Matplotlib | 3.10.8 | Import/version probe passed; no professional chart style verified. |
| pandas | 3.1.1 | Import/version probe passed. |
| NumPy | 2.4.6 in main env | Compatible with main GIS environment; incompatible with Blender's `<2` requirement, hence isolation. |

See `verification/geospatial_runtime.txt` and `verification/raster_runtime.txt`. **GDAL/OGR CLI and the `osgeo` Python binding are not installed**; the wheel-based Rasterio/Fiona/GeoPandas route is the verified workflow.

## Narration and audio

| Tool | Version / status | Verified boundary |
|---|---|---|
| Piper TTS | 1.8.0 | Python import and CLI help passed. **No voice model exists locally; speech synthesis NOT TESTED.** |
| ONNX Runtime | 1.31.1 | Installed as Piper dependency; model inference not tested. |
| SoundFile | 0.13.1 | Installed; no listening or speech-quality test. |
| Edge TTS client | 7.3.1 | Package installed. Earlier network synthesis failed; no current online synthesis claim. |
| FFmpeg audio | n9.0.2 build | loudnorm, resampling and rubberband support present in build configuration; no new audio mix generated. |
| SoX / standalone Rubberband | Absent | Not necessary because the selected FFmpeg build includes libsoxr/librubberband. |

## Installed but NOT operational

| Package | State |
|---|---|
| Blender Python (`bpy`) 4.5.16 | Installed in isolated `.venv-blender`; import fails: `libXrender.so.1` missing. **Not runtime verified.** Standalone `blender` CLI absent. |
| Manim Community | Not installed. Installation stopped at native Cairo/Pango dependency resolution. `.venv-manim` exists but is not a Manim runtime. |

Exact package lists: `environment/main_requirements_frozen.txt`, `environment/blender_requirements_frozen.txt`, and `environment/manim_requirements_frozen.txt`.

## Repository integrations that exist in code

- **Research:** Wikimedia/Wikipedia API discovery; owner-imported evidence ledgers; optional Groq and Ollama script drafting. Live research/provider calls were not exercised in this audit.
- **Assets:** Wikimedia Commons, official Pexels and Pixabay API adapters, local registered music; rights metadata, hashes and allowlisted downloads. API credentials and live asset searches were not tested.
- **Maps:** pinned Natural Earth 1:110m and 1:50m data, country zoom/highlight frames, route/marker coordinates with source requirements. No satellite provider integration exists.
- **Narration:** Edge TTS, eSpeak NG and Piper code paths with measured SRT generation. No eSpeak/Piper executable was initially available; Piper package is now present but has no voice model.
- **Graphics:** Remotion compositions, Pillow SVG/charts, Blender and Manim adapters. Adapters do not prove engine usability; both are currently blocked as described above.
- **Image generation:** no repository integration for DALL·E, Stable Diffusion, Midjourney, Leonardo, etc. No image-generation capability is claimed.
- **Publishing:** intentionally fail-closed. No deployment or publication performed.

Installation is not evidence of professional output. See `PRODUCTION_READINESS_AUDIT.md` for the capability decision.
