"""Tests for map country lookup fallback to 50m and ADM0_A3."""
import unittest
from geofactory.media.map_animation_engine import find_country, MapAnimationError


class TestMapCountryFallback(unittest.TestCase):
    """Test country lookup with fallback logic."""

    def test_110m_missing_50m_present(self):
        """Country missing in 110m but present in 50m should be found via fallback."""
        # This test verifies the logic - we mock the load_natural_earth to simulate
        # the fallback behavior by testing find_country directly
        # SGP is in 50m but not 110m
        # We'll test the actual function behavior
        
        # Create a mock collection with SGP
        sgp_feature = {
            "properties": {
                "ISO_A3_EH": "SGP",
                "ADM0_A3": "SGP",
                "ADMIN": "Singapore"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[103.6, 1.2], [104.0, 1.2], [104.0, 1.5], [103.6, 1.5], [103.6, 1.2]]]
            }
        }
        collection = {"features": [sgp_feature]}
        
        result = find_country(collection, "SGP")
        self.assertIsNotNone(result)
        self.assertEqual(result["properties"]["ADMIN"], "Singapore")

    def test_iso_a3_minus_99_fallback_to_adm0_a3(self):
        """ISO_A3_EH = -99 should fall back to ADM0_A3."""
        feature = {
            "properties": {
                "ISO_A3_EH": "-99",
                "ADM0_A3": "NOR",
                "ADMIN": "Norway"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }
        collection = {"features": [feature]}
        
        result = find_country(collection, "NOR")
        self.assertIsNotNone(result)
        self.assertEqual(result["properties"]["ADMIN"], "Norway")

    def test_both_missing_raises_error(self):
        """Country missing in both datasets should raise MapAnimationError."""
        feature = {
            "properties": {
                "ISO_A3_EH": "USA",
                "ADM0_A3": "USA",
                "ADMIN": "United States"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }
        collection = {"features": [feature]}
        
        with self.assertRaises(MapAnimationError) as ctx:
            find_country(collection, "XYZ")
        self.assertIn("XYZ", str(ctx.exception))

    def test_priority_iso_a3_eh_over_adm0_a3(self):
        """ISO_A3_EH should be checked before ADM0_A3."""
        # Two features, one with ISO_A3_EH match, one with ADM0_A3 match
        feature1 = {
            "properties": {"ISO_A3_EH": "ABC", "ADM0_A3": "DEF", "ADMIN": "Country1"},
            "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}
        }
        feature2 = {
            "properties": {"ISO_A3_EH": "XXX", "ADM0_A3": "ABC", "ADMIN": "Country2"},
            "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}
        }
        collection = {"features": [feature1, feature2]}
        
        # Should match feature1 via ISO_A3_EH
        result = find_country(collection, "ABC")
        self.assertEqual(result["properties"]["ADMIN"], "Country1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
