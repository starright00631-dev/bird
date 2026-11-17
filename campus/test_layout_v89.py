"""Tests for BNBU v89 layout-corrected Blender-compatible 3D scene (Issue #13)."""
from __future__ import annotations

import json
import math
import struct
import unittest
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
DATA = HERE / "generated"
REG = HERE / "registry"


def unpack_glb(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    assert raw[:4] == b"glTF"
    ver, total_len = struct.unpack_from("<II", raw, 4)
    assert ver == 2 and total_len == len(raw)
    assert len(raw) % 4 == 0
    off = 12
    chunks = []
    while off < len(raw):
        clen, ctype = struct.unpack_from("<I4s", raw, off)
        assert clen % 4 == 0
        off += 8
        chunks.append((ctype, raw[off : off + clen]))
        off += clen
    assert chunks[0][0] == b"JSON" and chunks[1][0] == b"BIN\0"
    doc = json.loads(chunks[0][1].decode("utf-8").rstrip(" \t\r\n\0"))
    return doc, chunks[1][1]


def extract_prim(doc: dict, binary: bytes, prim: dict):
    acc_p = doc["accessors"][prim["attributes"]["POSITION"]]
    bv_p = doc["bufferViews"][acc_p["bufferView"]]
    off_p = bv_p.get("byteOffset", 0) + acc_p.get("byteOffset", 0)
    pos = np.frombuffer(binary, dtype="<f4", count=acc_p["count"] * 3, offset=off_p).reshape(-1, 3)

    acc_n = doc["accessors"][prim["attributes"]["NORMAL"]]
    bv_n = doc["bufferViews"][acc_n["bufferView"]]
    off_n = bv_n.get("byteOffset", 0) + acc_n.get("byteOffset", 0)
    nrm = np.frombuffer(binary, dtype="<f4", count=acc_n["count"] * 3, offset=off_n).reshape(-1, 3)

    acc_i = doc["accessors"][prim["indices"]]
    bv_i = doc["bufferViews"][acc_i["bufferView"]]
    off_i = bv_i.get("byteOffset", 0) + acc_i.get("byteOffset", 0)
    dt = {5123: "<u2", 5125: "<u4"}[acc_i["componentType"]]
    ind = np.frombuffer(binary, dtype=dt, count=acc_i["count"], offset=off_i).reshape(-1, 3)
    return pos, nrm, ind, acc_p


class TestLayoutV89(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glb_path = DATA / "BNBU_v89_LAYOUT_CORRECTED.glb"
        cls.edges_path = DATA / "BNBU_v89_SHARP_FEATURE_EDGES_DISPLAY_ONLY.glb"
        cls.atlas = json.loads((DATA / "BNBU_v89_ARCHITECTURE_COMPONENT_ATLAS.json").read_text("utf-8"))
        cls.audit = json.loads((DATA / "BNBU_v89_LAYOUT_AUDIT_REPORT.json").read_text("utf-8"))
        cls.registry = json.loads((REG / "BNBU_v89_BUILDING_ASSET_REGISTRY.json").read_text("utf-8"))
        cls.geojson = json.loads((DATA / "BNBU_v89_RESOLVED_REFERENCES.geojson").read_text("utf-8"))
        cls.doc, cls.bin = unpack_glb(cls.glb_path)

    def test_gltf2_blender_compatibility_and_normals(self):
        self.assertEqual(self.doc["asset"]["version"], "2.0")
        world = self.doc["nodes"][0]
        self.assertEqual(world["name"], "world")
        expected_q = [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]
        for a, b in zip(world["rotation"], expected_q):
            self.assertAlmostEqual(a, b, places=5)

        total_tris = 0
        for mesh in self.doc["meshes"]:
            for prim in mesh["primitives"]:
                self.assertIn("POSITION", prim["attributes"])
                self.assertIn("NORMAL", prim["attributes"])
                self.assertIn("indices", prim)
                pos, nrm, ind, acc_p = extract_prim(self.doc, self.bin, prim)
                self.assertTrue(np.all(np.isfinite(pos)))
                self.assertTrue(np.all(np.isfinite(nrm)))
                lengths = np.linalg.norm(nrm, axis=1)
                self.assertTrue(np.all(np.abs(lengths - 1.0) < 1e-3), f"Non-unit normals in {mesh['name']}")
                self.assertTrue(np.all(ind < len(pos)))
                for k in range(3):
                    self.assertAlmostEqual(float(pos[:, k].min()), acc_p["min"][k], places=3)
                    self.assertAlmostEqual(float(pos[:, k].max()), acc_p["max"][k], places=3)
                # Zero degenerate triangles
                tris = pos[ind]
                areas = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
                self.assertTrue(np.all(areas > 1e-8), f"Degenerate tri in {mesh['name']}")
                total_tris += len(ind)
        self.assertGreater(total_tris, 300000)

        # Trimesh scene load check (matches external Blender/glTF importer validation)
        scene = trimesh.load(str(self.glb_path), file_type="glb", force="scene")
        self.assertGreater(len(scene.geometry), 400)
        edge_scene = trimesh.load(str(self.edges_path), file_type="glb", force="scene")
        self.assertGreaterEqual(len(edge_scene.geometry), 5)

    def test_issue13_building_layout_accuracy(self):
        s = self.audit["summary"]
        self.assertEqual(s["buildings_evaluated"], 41)
        self.assertGreaterEqual(s["mean_iou_after_v89"], 0.96)
        self.assertGreaterEqual(s["min_iou_after_v89"], 0.85)
        self.assertLess(s["mean_iou_before_v88"], 0.40)

        by_id = {b["id"]: b for b in self.audit["buildings"]}
        for bid, b in by_id.items():
            self.assertLess(b["after_centroid_err_m"], 0.9, f"{bid} centroid err too high")
            if bid != "P2_CIRCULAR_COMMONS":
                self.assertGreaterEqual(b["after_iou"], 0.95, f"{bid} IoU below 0.95")
                self.assertLess(abs(b["after_angle_err_deg"]), 1.5, f"{bid} angle err")

        # Key regressions fixed
        self.assertGreaterEqual(by_id["D1"]["after_iou"], 0.98)
        self.assertGreaterEqual(by_id["T5"]["after_iou"], 0.98)
        self.assertGreaterEqual(by_id["T7"]["after_iou"], 0.98)
        self.assertGreaterEqual(by_id["T8"]["after_iou"], 0.98)
        self.assertGreaterEqual(by_id["V29"]["after_iou"], 0.98)
        self.assertGreaterEqual(by_id["CC"]["after_iou"], 0.98)
        self.assertLess(by_id["P2_CIRCULAR_COMMONS"]["after_centroid_err_m"], 0.1)
        self.assertGreater(by_id["P2_LRC_LAB_COMPLEX"]["after_iou"], 0.95)

    def test_water_sports_bridges_and_village_locations(self):
        names = {n.get("name", "") for n in self.doc["nodes"] if "mesh" in n}
        # False road/hillside lakes removed
        for bad in ("LAKE_01", "LAKE_03", "LAKE_04"):
            self.assertNotIn(bad, names)
        self.assertIn("LAKE_00", names)
        self.assertIn("LAKE_02", names)

        # All 6 academic bridges present
        for k in range(6):
            self.assertIn(f"V52_LEVEL2_PEDESTRIAN_CONNECTION_0{k}_CLOSED_SLAB_EXISTING_TOPOGRAPHY", names)

        # CC must NOT intersect LAKE_00
        def node_xy(node_name):
            idx = next(i for i, n in enumerate(self.doc["nodes"]) if n.get("name") == node_name)
            mesh = self.doc["meshes"][self.doc["nodes"][idx]["mesh"]]
            polys = []
            for p in mesh["primitives"]:
                pos, _, ind, _ = extract_prim(self.doc, self.bin, p)
                for t in pos[ind]:
                    poly = Polygon([(t[0, 0], t[0, 1]), (t[1, 0], t[1, 1]), (t[2, 0], t[2, 1])])
                    if poly.is_valid and poly.area > 1e-4:
                        polys.append(poly)
            return unary_union(polys)

        cc_fp = node_xy("MAIN_CC")
        lake00_fp = node_xy("LAKE_00")
        self.assertAlmostEqual(cc_fp.intersection(lake00_fp).area, 0.0, places=3)

        # Sports park must be at south campus (local Y between 600 and 860, NOT > 900)
        for req in ("SPORTS_PARK_TRACK", "SPORTS_PARK_PITCH", "V89_SPORTS_PARK_TENNIS_COURT_01", "V89_SPORTS_PARK_BASKETBALL_COURT_01"):
            self.assertIn(req, names)
        track_idx = next(i for i, n in enumerate(self.doc["nodes"]) if n.get("name") == "SPORTS_PARK_TRACK")
        pos, _, _, _ = extract_prim(self.doc, self.bin, self.doc["meshes"][self.doc["nodes"][track_idx]["mesh"]]["primitives"][0])
        self.assertGreater(float(pos[:, 1].mean()), 620.0)
        self.assertLess(float(pos[:, 1].mean()), 860.0)

        # Huitong villas on south village (180 < Y < 370) with pitched roof height > 3m
        v14_idx = next(i for i, n in enumerate(self.doc["nodes"]) if n.get("name") == "V14_LIVING_VILLAGE_HUITONG_ROOFS_VERIFIED")
        vpos, _, _, _ = extract_prim(self.doc, self.bin, self.doc["meshes"][self.doc["nodes"][v14_idx]["mesh"]]["primitives"][0])
        self.assertGreater(float(vpos[:, 1].mean()), 180.0)
        self.assertLess(float(vpos[:, 1].mean()), 370.0)
        self.assertGreater(float(vpos[:, 2].max()), 7.0)

    def test_scientific_evidence_guardrails(self):
        self.assertEqual(self.atlas["version"], "v89")
        self.assertEqual(self.atlas["building_count"], 30)
        self.assertEqual(self.atlas["total_mapped_assets"], 41)
        self.assertEqual(self.atlas["new_surveyed_glazing_area"], 0)
        self.assertIsNone(self.atlas["window_panel_count_measured"])
        self.assertIn("CTV_SMALL_HOUSE", self.atlas["quarantined_hypotheses"])
        for n in self.doc["nodes"]:
            if "mesh" in n:
                ex = n.get("extras", {})
                self.assertFalse(ex.get("is_surveyed", False))
                self.assertFalse(ex.get("bird_glass_denominator", False))
        for item in self.registry["mapped_assets"]:
            self.assertFalse(item["is_surveyed"])
            self.assertFalse(item["birdstrike_area_eligible"])


if __name__ == "__main__":
    unittest.main()
