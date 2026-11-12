"""v69: waterproof model geometry and source-bound seasonal wetland assertions."""
from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path

from build_v65 import source_bytes
from build_v66 import hierarchical_scene
from refine_waterfront_v69 import build, decode_glb, geometry_digest

ROOT=Path(__file__).resolve().parent

class TestBNBUWaterfront(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/"generated/BNBU_v66_SEMANTIC_Y_UP.glb").read_bytes()
        cls.output,cls.report=build(cls.source)
        cls.before,cls.raw_before=decode_glb(cls.source)
        cls.after,cls.raw_after=decode_glb(cls.output)
    def test_all_geometry_accessors_and_scene_nodes_unchanged(self):
        self.assertEqual(len(self.before["meshes"]),1377)
        self.assertEqual(len(self.after["meshes"]),1377)
        self.assertEqual(self.before["nodes"],self.after["nodes"])
        self.assertEqual(self.before["scenes"],self.after["scenes"])
        self.assertEqual(self.before["accessors"],self.after["accessors"])
        self.assertEqual(self.before["bufferViews"],self.after["bufferViews"])
        self.assertEqual(geometry_digest(self.before,self.raw_before),
                         geometry_digest(self.after,self.raw_after))
        self.assertTrue(self.report["position_index_geometry_unchanged"])
        self.assertEqual(self.report["source_sha256"],hashlib.sha256(self.source).hexdigest())
    def test_exact_water_shore_and_wetland_meshes_modified(self):
        self.assertEqual(self.report["edited"]["existing_water"],5)
        self.assertEqual(self.report["edited"]["existing_shore"],5)
        self.assertEqual(self.report["edited"]["seam"],5)
        self.assertEqual(self.report["edited"]["wetland_water"],1)
        self.assertEqual(self.report["edited"]["wetland_bank"],1)
        self.assertEqual(self.report["edited"]["wetland_ground"],1)
        self.assertEqual(self.report["edited"]["recolored_vertices"],95984)
        self.assertIn("KHR_materials_clearcoat",self.after["extensionsUsed"])
        original_nodes={n["name"]:n for n in self.before["nodes"] if n.get("name")}
        modified_nodes={n["name"]:n for n in self.after["nodes"] if n.get("name")}
        for name in ["LAKE_%02d"%i for i in range(5)]:
            m=modified_nodes[name]["mesh"]
            self.assertIn("material",self.after["meshes"][m]["primitives"][0])
            self.assertEqual(original_nodes[name]["mesh"],m)
    def test_seasonal_real_ponds_not_falsely_identified(self):
        info=self.report["source_constraints"]
        self.assertIn("two freshwater ponds",info["east_hill_ponds"])
        self.assertIn("NOT identified",info["archived_phase_ii_wetland"])
        self.assertIn("official",info["east_hill_ponds"].lower())
        self.assertTrue(self.report["prohibited"]["invented_pond_mesh"])
        self.assertTrue(self.report["prohibited"]["new_surveyed_waterline"])
    def test_output_round_trip_and_bounding_box_meta(self):
        data,report=build(self.source)
        self.assertEqual(data,self.output)
        self.assertEqual(report,self.report)
        self.assertEqual(self.after["meshes"][0]["primitives"][0]["indices"],
                         self.before["meshes"][0]["primitives"][0]["indices"])
        self.assertIn("source_evidence_urls",self.after["asset"]["extras"]["v69_waterfront"])

if __name__=="__main__":
    unittest.main()
