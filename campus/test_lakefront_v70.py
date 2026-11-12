"""Regression for source-derived, visibly distinct, non-metric lakefront detail."""
import json
import unittest
from pathlib import Path

from build_lakefront_v70 import BOARD, STAIR, OUT, build

class TestV70(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=build()
    def test_source_bound_rail(self):
        r=self.report
        self.assertEqual(r["original_meshes"],1377)
        self.assertEqual(r["original_gis_features"],522)
        self.assertEqual(r["existing_deck_node"],BOARD)
        self.assertGreater(r["deck_polygon_area_m2_model_only"],480)
        self.assertGreater(r["over_lake_area_m2_model_only"],400)
        self.assertGreater(r["rail_m_path_model_only"],210)
        self.assertLess(r["rail_m_path_model_only"],250)
        self.assertGreater(len(r["railing_xy_polylines_local"][0]),100)
        self.assertEqual(r["role"],"DISPLAY_ONLY_NO_METRIC_GEOMETRY")
        self.assertTrue(r["source_glb_sha256"])
        self.assertEqual(json.loads(OUT.read_text()),r)
    def test_declared_uncertainty_and_collision_warning(self):
        r=self.report
        self.assertEqual(r["validation_flags"][0]["node"],STAIR)
        self.assertGreater(r["validation_flags"][0]["model_plan_overlap_m2"],47)
        self.assertIn("DO NOT",r["validation_flags"][0]["action"])
        self.assertTrue(any("not" in s for s in r["rules"]))
    def test_polyline_referenced_to_local_deck_not_hill_pond(self):
        r=self.report
        for line in r["railing_xy_polylines_local"]:
            for x,y,z in line:
                self.assertGreater(x,175)
                self.assertLess(x,327)
                self.assertGreater(y,-140)
                self.assertLess(y,-37)
                self.assertGreater(z,.5)
                self.assertLess(z,1.5)
        self.assertEqual(r["water_node"],"LAKE_00")
        self.assertEqual(len(r["photo_evidence"]),4)

if __name__=="__main__":
    unittest.main()
