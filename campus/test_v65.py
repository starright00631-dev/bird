"""Regression checks for geometry-preserving BNBU display correction."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from build_v65 import build, display_glb, reconcile_geojson, source_bytes, unpack_glb


class TestBNBUv65(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glb = source_bytes("BNBU_v64_ACTIVE.glb")
        cls.geo = source_bytes("BNBU_v64_ACTIVE.geojson")

    def test_world_axes_and_mesh_integrity(self):
        original, original_chunks = unpack_glb(self.glb)
        updated, meta = display_glb(self.glb)
        new, new_chunks = unpack_glb(updated)
        self.assertEqual(new["nodes"][0]["rotation"],
                         [-math.sqrt(.5), 0.0, 0.0, math.sqrt(.5)])
        self.assertEqual(len(new["meshes"]), 1377)
        self.assertEqual(new["meshes"], original["meshes"])
        self.assertEqual(new["accessors"], original["accessors"])
        self.assertEqual(new["bufferViews"], original["bufferViews"])
        self.assertEqual(new["materials"], original["materials"])
        self.assertEqual(new_chunks[1:], original_chunks[1:])
        self.assertEqual(meta["source_sha256"], hashlib.sha256(self.glb).hexdigest())
        self.assertNotEqual(meta["display_sha256"], meta["source_sha256"])

    def test_references_without_geometry_creation(self):
        new, stats = reconcile_geojson(self.geo, self.glb)
        original = json.loads(self.geo)
        corrected = json.loads(new)
        self.assertEqual(stats["gis_features"], 522)
        self.assertEqual(stats["render_alias_repairs"], 10)
        self.assertEqual(stats["unresolved_legacy_references"], 102)
        for a, b in zip(original["features"], corrected["features"]):
            self.assertEqual(a["geometry"], b["geometry"])
            for k, v in a["properties"].items():
                self.assertEqual(v, b["properties"][k])
        self.assertEqual(len(corrected["features"]), len(original["features"]))
        self.assertFalse(any("VILLA" in (x["properties"].get("render_model_node") or "").upper()
                             for x in corrected["features"]))

    def test_artifact_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            summary = build(Path(d))
            self.assertEqual(summary["display"]["meshes"], 1377)
            self.assertTrue((Path(d) / "BNBU_v65_DISPLAY_Y_UP.glb").is_file())
            self.assertTrue((Path(d) / "BNBU_v65_RENDER_REFERENCES.geojson").is_file())
            self.assertTrue((Path(d) / "v65_integrity_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
