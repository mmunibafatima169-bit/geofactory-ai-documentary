# Phase 2 — Part 2: Geographic and 3D capabilities

**Date:** 2026-11-11 UTC  
**Result:** **GIS/processing and architecture integration implemented; Blender/Manim runtime completion remains blocked by Part 1**  
**Video generated or rendered:** none  
**External satellite imagery downloaded:** none  
**Source samples/environments overwritten:** none  
**Commit, push or deployment:** none

## Task status

| Task | Result | Evidence |
|---|---|---|
| Audit/improve GIS using QGIS/GDAL/Python | **IMPLEMENTED with wheel-based GIS** | Actual vector/CRS/raster operations and geometry validation |
| Reliable satellite acquisition/processing | **IMPLEMENTED; live provider NOT TESTED** | STAC query/allowlist/download tests and RGB/cloud-mask processing tests |
| DEM/elevation/terrain processing | **IMPLEMENTED on synthetic data** | Terrarium decode, hillshade and actual GeoTIFF reprojection/read-back |
| Repair two Natural Earth geometries | **PASS** | Derived 177-feature file, 2→0 invalid, original unchanged |
| Configure reusable Blender terrain/environment/camera | **CONFIGURATION IMPLEMENTED; runtime BLOCKED** | Typed config + generic scene builder + fail-closed preflight |
| Configure Manim technical explanations | **CONFIGURATION IMPLEMENTED; runtime BLOCKED** | Typed scientific config + generic scene + fail-closed preflight |
| Integrate into Python architecture | **IMPLEMENTED** | `PreproductionPlan` → preparation jobs; no disconnected demo pipeline |

## 1. GIS/GDAL integration

### Actual environment

- GeoPandas 1.2.0, Shapely 2.2.0, PyProj 3.7.2 / PROJ 9.5.1.
- Rasterio 1.4.4 with bundled GDAL 3.10.3.
- Fiona 1.10.1 with bundled GDAL 3.9.2.
- QGIS, `gdalinfo`, `ogr2ogr` and the native `osgeo` binding remain absent. They were not falsely reported as installed.

The existing wheel-based route is sufficient for the implemented headless processing. QGIS remains an optional human cartographic-review application, not a dependency of the Python orchestrator. Fiona and Rasterio bundle different GDAL versions; production artifacts record which library performed each operation and avoid mixing native bindings implicitly.

### New `geofactory/production/geospatial.py`

- Derived-only `make_valid` repair with source/destination hashes.
- Preserves row count and attributes; rejects missing CRS and invalid read-back.
- Area-change guard for non-zero source areas.
- Handles zero-signed-area bow-ties explicitly.
- Removes only non-areal repair fragments; never simplifies source polygons.
- Records disputed-boundary non-normalization policy.
- Explicit vector reprojection into a new derived file.

## 2. Natural Earth repair — actual result

Source: `studio/remotion/public/ne110.geojson`  
Source SHA-256: `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`  
Derived: `production_readiness/part2/derived/ne110_validated.geojson`  
Derived SHA-256: `f19291e22c081d3a82dcc2b5dee3e09f9a3cb03678d5fb5d45b2ce4852ebbc31`

| Feature | Invalid cause | Repair | Relative area change |
|---|---|---|---|
| United States of America, index 4 | Self-intersection at approximately −140.986, 69.712 | MultiPolygon → MultiPolygon via `make_valid` | `5.0649856997555725e-15` |
| Sudan, index 14 | Self-intersection at approximately 33.9633928, 9.4642850 | Polygon → MultiPolygon via `make_valid` | `1.0048789891503534e-09` |

- Feature count: **177 before / 177 after**.
- Invalid geometries: **2 before / 0 after**.
- CRS remains EPSG:4326.
- Attributes unchanged; original source file unchanged.
- Licence remains **Natural Earth Public Domain**; source and terms URLs are recorded.
- This is a topological derived repair, not an editorial endorsement or normalization of disputed borders.

Evidence: `derived/ne110_repair_report.json` and `logs/natural_earth_repair.txt`.

## 3. Satellite imagery workflow

### `geofactory/production/imagery.py`

Implements a provider-configured STAC client with:

- HTTPS STAC search, collections, bbox, datetime, cloud-cover and result-limit constraints.
- Bounded response sizes and explicit provider download-host allowlists.
- Acquisition timestamp, item ID, cloud cover, bbox and asset-role records.
- Atomic bounded downloads, SHA-256, licence/attribution propagation and mandatory rights review.
- Injectable transport for deterministic offline tests; no provider credentials are embedded.

No provider is silently treated as freely licensed. A production provider configuration must supply its current licence, licence URL, attribution and permitted asset hosts. Copernicus/ESA or another provider still requires live endpoint, collection/asset-role and current-terms verification before use.

### `geofactory/production/raster.py`

- Three-band percentile RGB stretch to display uint8, retaining original rasters separately.
- Sentinel-2 QA60 opaque/cirrus cloud-bit masking.
- Invalid/no-valid-pixel and malformed-array rejection.

Tests used a synthetic STAC response and synthetic arrays. They prove query formation, allowlist enforcement, bounded download bookkeeping and processing logic—not live satellite availability or visual image quality.

**Live acquisition status: NOT TESTED / network-provider setup required.**

## 4. DEM and terrain processing

Implemented in `raster.py`:

- Mapzen Terrarium RGB decoding: `R×256 + G + B/256 − 32768` metres.
- Bounded 2D-array validation.
- Slope/aspect-based uint8 hillshade with configurable cell size, sun azimuth and altitude.
- Single-band DEM reprojection with bilinear resampling, nodata propagation, compression and vertical-datum metadata retention/warning.

Actual verification created an 8×8 synthetic EPSG:4326 DEM, reprojected it to EPSG:3857 and successfully read it back. The test is synthetic and does not assert a real-world elevation or terrain appearance. Terrarium zero decoding returned exactly `0.0` metres.

Evidence: `logs/dem_processing.txt`, `derived/synthetic_dem.tif`, and `derived/synthetic_dem_3857.tif`.

Production DEM acquisition must record the selected dataset, native/vertical datum, resolution, source licence and attribution. Mapzen tiles combine sources with different attribution obligations; no blanket public-domain assumption is made.

## 5. Reusable Blender configuration — not runtime verified

New components:

- `production/scene_configs.py`: `TerrainConfig`, `EnvironmentConfig`, `CameraKey`, `BlenderSceneConfig`.
- `studio/blender/terrain_scene.py`: generic editable-scene builder with DEM mesh, terrain attribution/metadata, lighting, material and animated camera keyframes.
- `production/engine_adapters.py`: probes the existing isolated `.venv-blender` interpreter and fails closed.
- `production/preparation_pipeline.py`: connects scene intents to preparation jobs.

The builder saves an editable `.blend` and contains no video-render operator. It is not Venice-specific and does not create a disconnected demo.

Actual preflight still fails:

```text
ImportError: libXrender.so.1: cannot open shared object file: No such file or directory
runtime_verified=false; render_tested=false
```

Therefore no `.blend` was generated and no Blender execution is claimed. DEM input sampling and terrain appearance remain **NOT TESTED** until Part 1's native blocker is repaired. For production, a floating-point DEM interchange such as EXR should be validated rather than assuming display PNG precision.

## 6. Reusable Manim configuration — not runtime verified

- `ScientificExplanationConfig` supports chart/formula/process contract types, aligned values/labels, units, source IDs and explanatory notes.
- `studio/manim/technical_explanation.py` implements the first reusable `bar_comparison` adapter and rejects unsupported types rather than silently substituting.
- Scene syntax compilation passes without importing Manim.
- No animation or render call was made.

Actual preflight remains:

```text
ModuleNotFoundError: No module named 'manim'
installed=false; runtime_verified=false
```

Manim execution, text layout, scientific notation and output quality are **NOT TESTED**.

## 7. Production integration

`preparation_pipeline.py` consumes the existing `PreproductionPlan` and produces typed jobs for both preparation and motion engines. Each job includes:

- scene ID and engine;
- operation and input/output contracts;
- `executable` flag;
- exact runtime blocker;
- no implicit execution or render path.

Missing engine registrations default to unavailable. GIS and Blender jobs are produced together for terrain scenes, connecting geographic preparation to 3D scene creation. This preserves the existing Python orchestrator and prevents a blocked Blender/Manim engine from being marked ready.

## 8. Tests and preservation

Full suite:

```text
Ran 65 tests in 7.651s
OK (skipped=5)
```

Nine new Part 2 tests cover:

1. Derived-only invalid polygon repair.
2. RGB stretch and QA60 cloud masks.
3. Terrarium decoding and hillshade.
4. STAC query/download/provenance.
5. Download-host fail-closed behavior.
6. Reusable terrain/environment/camera configuration.
7. Scientific data/source validation.
8. Engine preflight fail-closed behavior.
9. Plan-to-GIS/engine preparation integration without execution.

Additional checks: module compilation passed; `pip check` clean; original Natural Earth and both sample-video hashes unchanged. No still-image or video rendering was needed for these tests.

Logs: `production_readiness/part2/logs/`.

## Remaining blockers and next requirements

1. Part 1 native/network blockers still prevent actual Blender and Manim execution.
2. Satellite provider endpoint, licence, collection/asset roles and live COG downloads need a permitted live-provider validation.
3. Real DEM/imagery visual quality, registration, cloud removal and terrain appearance remain untested.
4. QGIS Desktop remains optional and uninstalled; native GDAL CLI is not required for the current implemented route.
5. Blender terrain input precision/performance and Manim execution must be verified after runtime repair.
6. These additions are production modules and contracts, not evidence that professional geographic/3D visuals have already been produced.

**Stop after Part 2. Part 3 has not been started.**
