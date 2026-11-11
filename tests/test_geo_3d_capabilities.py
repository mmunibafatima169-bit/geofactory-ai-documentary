import io
import json
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

from geofactory.production.capabilities import Capability
from geofactory.production.engine_adapters import build_preparation_job
from geofactory.production.preparation_pipeline import plan_preparation, preparation_summary
from geofactory.production.direction import build_preproduction_plan
from geofactory.production.models import DocumentaryProfile
from geofactory.production.geospatial import repair_vector_derivative
from geofactory.production.imagery import ImageryError, ImageryProvider, STACClient
from geofactory.production.raster import cloud_valid_mask, decode_terrarium, hillshade, robust_rgb_stretch
from geofactory.production.scene_configs import BlenderSceneConfig, CameraKey, EnvironmentConfig, ScientificExplanationConfig, TerrainConfig


class GeoPreparationTests(unittest.TestCase):
    def test_invalid_polygon_repaired_only_in_derivative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, derived, report_path = root / "source.geojson", root / "derived.geojson", root / "report.json"
            frame = gpd.GeoDataFrame({"NAME": ["valid", "invalid"]}, geometry=[Polygon([(0, 0), (1, 0), (1, 1)]), Polygon([(2, 2), (3, 3), (2, 3), (3, 2)])], crs="EPSG:4326")
            frame.to_file(source, driver="GeoJSON")
            before = source.read_bytes()
            report = repair_vector_derivative(source, derived, report_path, dataset_name="test", dataset_version="1", licence="CC0-1.0", licence_url="https://creativecommons.org/publicdomain/zero/1.0/", source_url="https://example.com/source")
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(report["invalid_before_after"], [1, 0])
            self.assertTrue(gpd.read_file(derived).geometry.is_valid.all())

    def test_rgb_stretch_and_cloud_mask(self):
        red = np.array([[0, 100], [200, 300]], dtype=np.uint16)
        rgb = robust_rgb_stretch(red, red, red, lower_percentile=0, upper_percentile=100)
        self.assertEqual(rgb.shape, (3, 2, 2))
        self.assertEqual(int(rgb[0, 1, 1]), 255)
        qa = np.array([[0, 1 << 10], [1 << 11, 0]])
        self.assertEqual(cloud_valid_mask(qa).tolist(), [[True, False], [False, True]])

    def test_terrarium_decode_and_hillshade(self):
        elevation = np.zeros((1, 1))
        encoded = decode_terrarium(np.array([[128]]), np.array([[0]]), np.array([[0]]))
        np.testing.assert_array_equal(encoded, elevation)
        shaded = hillshade(np.arange(16).reshape(4, 4), 1.0)
        self.assertEqual(shaded.shape, (4, 4))
        self.assertEqual(shaded.dtype, np.uint8)


class ImageryTests(unittest.TestCase):
    def provider(self):
        return ImageryProvider("test", "https://catalogue.example/stac/search", ("sentinel-test",), ("assets.example",), "CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/", "Test provider attribution")

    def selection(self):
        return self.client.search((0.0, 0.0, 1.0, 1.0), "2025-01-01/2025-01-31")[0]

    def setUp(self):
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        feature = {"id": "item-1", "collection": "sentinel-test", "bbox": [0, 0, 1, 1], "properties": {"datetime": "2025-01-02T00:00:00Z", "eo:cloud_cover": 3.0}, "assets": {"B04": {"href": "https://assets.example/B04.tif"}}}
        self.payloads = []
        def transport(url, payload=None):
            self.payloads.append((url, payload))
            return Response(b"asset" if payload is None else json.dumps({"features": [feature]}).encode())
        self.client = STACClient(self.provider(), transport=transport)

    def test_stac_query_and_bounded_asset_download(self):
        selection = self.selection()
        self.assertEqual(selection.item_id, "item-1")
        self.assertEqual(self.payloads[0][1]["query"]["eo:cloud_cover"]["lte"], 20.0)
        with tempfile.TemporaryDirectory() as directory:
            record = self.client.download_asset(selection, "B04", Path(directory) / "B04.tif")
            self.assertTrue(record["rights_review_required"])
            self.assertEqual(record["bytes"], 5)

    def test_download_host_is_fail_closed(self):
        selection = self.selection()
        selection.assets["B04"] = "https://unapproved.example/B04.tif"
        with self.assertRaises(ImageryError):
            self.client.download_asset(selection, "B04", Path("unused.tif"))


class EngineConfigurationTests(unittest.TestCase):
    def test_terrain_and_camera_config_is_reusable(self):
        config = BlenderSceneConfig(TerrainConfig("dem.exr", None, 1.5, 128, "EGM2008", "Test DEM attribution"), EnvironmentConfig((0.1, 0.1, 0.1), 2.0, (30, 0, 45)), (CameraKey(1, (1, 1, 1), (0, 0, 0)), CameraKey(90, (2, 2, 2), (0, 0, 0))))
        self.assertEqual(config.to_dict()["terrain"]["vertical_exaggeration"], 1.5)

    def test_scientific_config_requires_aligned_sources(self):
        config = ScientificExplanationConfig("bar_comparison", "Measure", ("A",), (1.0,), "metres", ("src-1",), "Illustrative reconstruction")
        self.assertEqual(config.to_dict()["unit"], "metres")
        with self.assertRaises(ValueError):
            ScientificExplanationConfig("bar_comparison", "Bad", ("A", "B"), (1,), "m", (), "").validate()

    def test_preparation_job_fails_closed_when_runtime_blocked(self):
        blocked = Capability("blender", True, False, None, ".venv-blender/bin/python", "libXrender.so.1 missing")
        job = build_preparation_job("scene-001", "blender", blocked)
        self.assertFalse(job.executable)
        self.assertIn("libXrender", job.blocker)

    def test_plan_creates_integrated_gis_and_engine_jobs_without_execution(self):
        plan = build_preproduction_plan(DocumentaryProfile("infrastructure", "Terrain", "How does terrain affect the structure?"), [(0.0, 8.0, "The mountain terrain affects the foundation. [clm-one]")])
        capabilities = {"gis": Capability("gis", True, True, "1", ".venv/bin/python", "verified")}
        summary = preparation_summary(plan_preparation(plan, capabilities))
        self.assertFalse(summary["execution_performed"])
        self.assertFalse(summary["video_rendered"])
        self.assertGreaterEqual(summary["blocked_count"], 1)
        self.assertTrue(any(job["engine"] == "gis" for job in summary["jobs"]))


if __name__ == "__main__":
    unittest.main()
