import hashlib, os, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from audit_buildings_v89 import build, CORE_IDS

PACKAGE = Path(os.environ.get("BNBU_PACKAGE_ROOT", ".")).resolve()

class TestV89BuildingAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glb = PACKAGE / "generated/BNBU_v71_CONNECTED_LAKEFRONT.glb"
        cls.before = hashlib.sha256(cls.glb.read_bytes()).hexdigest()
        cls.audit = build(PACKAGE)

    def test_complete_inventory(self):
        self.assertEqual([x["id"] for x in self.audit["core_buildings"]], CORE_IDS)
        self.assertEqual(len(self.audit["extended_assets"]), 8)
        self.assertEqual(len(self.audit["core_buildings"]), 30)

    def test_all_registry_components_exist(self):
        for r in self.audit["core_buildings"] + self.audit["extended_assets"]:
            self.assertEqual(r["component_count"], len(r["story_edge_nodes"]) + len(r["glazing_surface_nodes"]) + len(r["opaque_frame_or_return_nodes"]) + len(r["balcony_or_rail_nodes"]) + len(r["stair_nodes"]) + len(r["roof_crossrib_nodes"]) + sum(v for k,v in r["component_category_counts"].items() if k not in {"story_edges","glazing","opaque_frame_or_return","balcony_and_rails","stairs"}))

    def test_v25_resolution_outlier(self):
        r = next(x for x in self.audit["core_buildings"] if x["id"] == "V25")
        m = next(x for x in r["primary_mesh_nodes"] if x["node"] == "MAIN_V25")
        self.assertEqual((m["vertices"], m["triangles"]), (62,120))
        self.assertEqual(len(m["z_levels_rounded_0_01"]), 2)

    def test_facade_findings(self):
        flags = {x["id"]:x for x in self.audit["defect_flags"]}
        self.assertIn("T1_PHOTO_BACKED_GLAZING_OMISSION", flags)
        self.assertIn("V_SERIES_FACADE_FEATURE_TYPE_GAP", flags)
        self.assertIn("D_SERIES_FACADE_FEATURE_MAPPING_GAP", flags)
        self.assertIn("P2_LRC_LAB_COMPLEX_UNMAPPED", flags)

    def test_t_series_glazing_classification(self):
        t = {x["id"]:len(x["glazing_surface_nodes"]) for x in self.audit["core_buildings"] if x["family"]=="T"}
        self.assertEqual(t, {"T1":0,"T2":7,"T3":3,"T4":4,"T5":0,"T6":0,"T7":0,"T8":0})
        t2 = next(x for x in self.audit["core_buildings"] if x["id"]=="T2")
        self.assertEqual(len(t2["opaque_frame_or_return_nodes"]), 36)

    def test_source_unchanged(self):
        self.assertEqual(hashlib.sha256(self.glb.read_bytes()).hexdigest(), self.before)

if __name__ == "__main__":
    unittest.main()
