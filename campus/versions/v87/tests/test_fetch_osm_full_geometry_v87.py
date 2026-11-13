"""Unit tests use a tiny synthetic test-way only; no fixture is campus geometry."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fetch_osm_full_geometry_v87 import validate_payload, build_query


class TestOSMFullGeometryValidation(unittest.TestCase):
    def setUp(self):
        self.expected = {"TEST": {"id": 99, "name_en": "TEST WAY", "nodes": [1, 2, 3, 1]}}
        self.payload = {"elements": [{
            "type": "way", "id": 99, "version": 1, "timestamp": "2026-01-01T00:00:00Z",
            "nodes": [1, 2, 3, 1],
            "tags": {"building": "university", "name:en": "TEST WAY"},
            "geometry": [
                {"lon": 113.0, "lat": 22.0}, {"lon": 113.001, "lat": 22.0},
                {"lon": 113.001, "lat": 22.001}, {"lon": 113.0, "lat": 22.0}
            ]
        }]}

    def test_closed_way_and_tags_pass(self):
        out = validate_payload(self.payload, self.expected)
        self.assertTrue(out["geometry_ready"])
        self.assertTrue(out["registration_eligible"])
        self.assertEqual(out["ways"]["TEST"]["node_count"], 4)

    def test_changed_node_sequence_blocks_registration_but_keeps_geometry(self):
        p = {"elements": [dict(self.payload["elements"][0], nodes=[1, 3, 2, 1])]}
        out = validate_payload(p, self.expected)
        self.assertTrue(out["geometry_ready"])
        self.assertFalse(out["registration_eligible"])

    def test_open_ring_is_rejected(self):
        p = {"elements": [dict(self.payload["elements"][0], nodes=[1, 2, 3, 4])]}
        with self.assertRaises(ValueError):
            validate_payload(p, self.expected)

    def test_invalid_coordinate_is_rejected(self):
        geom = list(self.payload["elements"][0]["geometry"])
        geom[1] = {"lon": 999, "lat": 22}
        p = {"elements": [dict(self.payload["elements"][0], geometry=geom)]}
        with self.assertRaises(ValueError):
            validate_payload(p, self.expected)

    def test_query_requests_full_geometry_not_bbox_center(self):
        q = build_query(self.expected)
        self.assertIn("out meta geom", q)
        self.assertNotIn("out center", q)


if __name__ == "__main__":
    unittest.main()