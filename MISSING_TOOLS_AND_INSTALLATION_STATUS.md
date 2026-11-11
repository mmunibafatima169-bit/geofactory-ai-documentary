# Missing tools and installation status

Audit date: 2026-11-10 UTC. No renderer was invoked. Commands and raw failures are retained in `production_readiness/installation/` and `production_readiness/verification/`.

## Decisions and outcomes

| Component | Why it is needed | Action and verified result | Status |
|---|---|---|---|
| **GIS Python stack** | Accurate vector/raster preparation, CRS transforms, geometry checks and terrain/imagery inputs | Installed GeoPandas, Shapely, PyProj, Rasterio, Fiona, Matplotlib and pandas. Vector read/reprojection and in-memory raster round trip passed. | **WORKING** |
| **Blender Python 4.5.16** | Reusable 3D terrain, engineering objects, cutaways and camera animation | 372.8 MiB wheel installed in `.venv-blender`; import fails on `libXrender.so.1`. Existing adapter expects a separate `blender` executable and cannot use this wheel automatically. | **INSTALLED, BLOCKED** |
| **Manim Community 0.22.1** | Mathematical/scientific constructions and exact explanatory animation | pip failed while building PyCairo/ManimPango because `pkg-config`, Cairo and Pango development dependencies are absent. | **NOT INSTALLED** |
| **GDAL/OGR CLI + `osgeo` binding** | Interoperable GIS inspection and conversion | Source build failed because `gdal-config` and native development headers are absent. Rasterio/Fiona wheels provide the required current raster/vector route instead. | **NOT INSTALLED; NOT CURRENTLY REQUIRED** |
| **QGIS Desktop** | Interactive cartographic review, complex layer styling and human GIS inspection | Not installed. It is not necessary for headless Python orchestration and would add heavy GUI/Qt dependencies to a 2-core/3.8-GiB host. | **DEFERRED / OPTIONAL DESKTOP TOOL** |
| **Piper TTS** | Offline, reproducible narration candidate without a per-request cloud dependency | Piper 1.8.0 import/help passed. No licensed ONNX voice model is present, so no synthesis or quality claim. | **RUNTIME PRESENT; VOICE MISSING** |
| **SoX / standalone Rubberband** | Audio analysis/processing | Not installed. Current FFmpeg already includes libsoxr/librubberband, so duplicate packages are unnecessary now. | **NOT NEEDED NOW** |
| **ImageMagick** | Contact sheets, asset transforms and image diagnostics | Existing ImageMagick 6 runtime verified. No reinstall. | **WORKING** |
| **Python / Remotion / FFmpeg** | Existing orchestrator, motion graphics and assembly | Existing installations retained. No unnecessary reinstall. | **WORKING WITH DOCUMENTED LIMITS** |
| **Satellite/aerial provider** | Dated, attributable imagery workflows | No provider credentials or integration. Not installed as a package because this requires a source/licensing decision, not blind dependency installation. | **MISSING ARCHITECTURE/PROVIDER** |
| **Image-generation provider** | Original conceptual reconstructions where footage cannot explain the subject | No integration. Not installed until editorial policy, provenance disclosure, model rights and provider are chosen. | **MISSING / DECISION REQUIRED** |
| **Natural professional TTS** | Benchmark-level narration quality | Piper requires an audition; Edge failed earlier; Arena speech is not a reusable repository provider. No local high-quality voice pipeline has passed listening QC. | **MISSING QUALITY VERIFICATION** |

## Exact native dependency blocker

`sudo -n` succeeds, so administrator privilege is available. The blocker is **outbound access to Debian repositories**, not sudo. `apt-get update` could not connect to `deb.debian.org` on port 80. The sandbox allowlist only permits GitHub, npm and PyPI hosts. Raw log: `production_readiness/installation/apt_update.log`.

When repository access is permitted, the manual repair is:

```bash
sudo apt-get update
sudo apt-get install -y \
  libxrender1 pkg-config libcairo2-dev libpango1.0-dev

# Verify Blender runtime, without rendering:
.venv-blender/bin/python -c 'import bpy; print(bpy.app.version_string)'

# Complete Manim in its isolated environment:
.venv-manim/bin/pip install manim==0.22.1
.venv-manim/bin/python -c 'import manim; print(manim.__version__)'
```

For the existing CLI adapter, install the official Blender distribution separately and place `blender` on PATH, **or** implement and test a new adapter for `.venv-blender`. Do not equate the `bpy` wheel with the standalone CLI. If native GDAL utilities are later required:

```bash
sudo apt-get install -y gdal-bin libgdal-dev
```

Then match the Python GDAL binding to the system `gdal-config --version`. Do not blindly reinstall it while Rasterio/Fiona wheels satisfy the workflow.

## Environment isolation

- `.venv`: orchestration, GIS, audio and Piper; `pip check` passes.
- `.venv-blender`: NumPy 1.26.4 and Blender 4.5.16; isolated because Blender requires NumPy `<2`, while current GIS requires NumPy `>=2`.
- `.venv-manim`: reserved isolated environment; Manim installation incomplete.
- `.venv-blender/` and `.venv-manim/` are excluded locally through `.git/info/exclude`; no dependency payloads are intended for Git.

## Disk and hardware implications

Approximately 15 GiB remains free. The Blender environment consumes about 944 MiB. With 2 cores, 3.8 GiB RAM, no swap and no exposed GPU, complex Cycles/EEVEE production and high-resolution terrain would be slow or memory constrained. A CPU import probe—even after repair—will not establish production throughput. Hardware benchmarking must wait for separately approved rendering.

## Failed attempts retained, not hidden

1. Manim 0.22.1: PyCairo metadata/build failure, missing `pkg-config`/Cairo.
2. Initial Rasterio 1.5.0 request: incompatible with Python 3.11; Rasterio 1.4.4 selected successfully.
3. Direct GDAL 3.10.3 binding: missing `gdal-config`; wheel-based GIS used instead.
4. First Blender install shared the main env and forced NumPy `<2`; it was isolated and removed from main to restore dependency consistency.
5. Blender import: missing `libXrender.so.1`.
6. Piper: package works, but no model means synthesis remains NOT TESTED.
