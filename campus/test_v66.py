"""v66 regression: scene hierarchy, mesh buffers, road/bridge taxonomy and GIS links."""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from build_v65 import display_glb, reconcile_geojson, source_bytes, unpack_glb
from build_v66 import (
    LAYERS, REPAIRED_GROUND, REPAIRED_STAIRS, build,
    classify_node, hierarchical_scene, rebind_geojson,
)


class TestBNBUv66(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_glb = source_bytes("BNBU_v64_ACTIVE.glb")
        cls.original_gis = source_bytes("BNBU_v64_ACTIVE.geojson")
        cls.v65glb, _ = display_glb(cls.original_glb)
        cls.v65gis, _ = reconcile_geojson(cls.original_gis, cls.original_glb)

    def test_taxonomy_is_physical_not_keyword_only(self):
        self.assertEqual(classify_node("V60_P1_EASTLAKE_BOARDWALK_PAIRED_PIER_13_PHOTO_SUPPORT_TYPE_UNSURVEYED"),
                         "elevated_boardwalk_unsurveyed")
        self.assertEqual(classify_node("V49_PHASEII_D1_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE"),
                         "ground_connectors_unsurveyed")
        self.assertEqual(classify_node("PHASEII_V12_PAVING_phaseII_west_road_concept_surface"),
                         "pedestrian_paving_unsurveyed")
        self.assertEqual(classify_node("V58_P2_ROUND_COMMONS_OPAQUE_SQUARE_ROOF_COPING_01_NON_GLASS"),
                         "architecture_opaque")
        self.assertEqual(classify_node("LAKE_00"), "water_unsurveyed")
        self.assertEqual(classify_node("SHORE_03"), "shore_unsurveyed")
        self.assertEqual(classify_node("ROAD_001"), "vehicle_roads_unsurveyed")
        self.assertEqual(classify_node("V53_TERRAIN_RELIEF_NORTH_RIDGE_NON_SURVEYED"),
                         "terrain_unsurveyed")

    def test_meshes_retain_original_positions_faces_and_materials(self):
        before, chunks_before = unpack_glb(self.v65glb)
        revised_glb, details = hierarchical_scene(self.v65glb)
        after, chunks_after = unpack_glb(revised_glb)
        self.assertEqual(chunks_after[1:], chunks_before[1:])
        self.assertEqual(before["meshes"], after["meshes"])
        self.assertEqual(before["accessors"], after["accessors"])
        self.assertEqual(before["bufferViews"], after["bufferViews"])
        self.assertEqual(before["materials"], after["materials"])
        self.assertEqual(before["nodes"][0]["rotation"], after["nodes"][0]["rotation"])
        self.assertEqual(details["mesh_count"], 1377)
        grouped = [after["nodes"][x] for x in after["nodes"][0]["children"]]
        self.assertEqual(len(grouped), details["hierarchy_nodes_added"])
        self.assertEqual(sum(len(x["children"]) for x in grouped), 1377)
        self.assertEqual(len(set(sum((x["children"] for x in grouped), []))), 1377)
        self.assertGreater(details["layer_counts"]["elevated_boardwalk_unsurveyed"], 0)
        self.assertEqual(sum(details["layer_counts"].values()), 1377)
        self.assertTrue(set(details["layer_counts"]).issubset(LAYERS))

    def test_102_old_references_restore_matching_inherited_geometry(self):
        revised_glb, _ = hierarchical_scene(self.v65glb)
        output, counts = rebind_geojson(self.v65gis, revised_glb)
        before = json.loads(self.v65gis)
        after = json.loads(output)
        self.assertEqual(counts["stair_render_links_repaired"], 96)
        self.assertEqual(counts["at_grade_links_repaired"], 6)
        self.assertEqual(counts["unresolved_render_links"], 0)
        self.assertEqual(counts["feature_count"], 522)
        for old, new in zip(before["features"], after["features"]):
            self.assertEqual(old["geometry"], new["geometry"], "GIS geometry must be immutable")
            for k, value in old["properties"].items():
                self.assertEqual(value, new["properties"][k], "Never replace source metadata")
        repaired = Counter(f["properties"]["model_node"] for f in after["features"]
                           if f["properties"].get("v66_edit_type"))
        self.assertEqual(sum(repaired.values()), 102)
        self.assertEqual(set(repaired), set(REPAIRED_GROUND) | set(REPAIRED_STAIRS))
        self.assertFalse(any("CTV" in (f["properties"].get("render_model_node") or "").upper()
                             and "VILLA" in (f["properties"].get("render_model_node") or "").upper()
                             for f in after["features"]))

    def test_outputs_are_real_files_not_report_only(self):
        with tempfile.TemporaryDirectory() as directory:
            report = build(Path(directory))
            self.assertTrue(report["scene"]["geometry_bytes_identical"])
            for basename in ["BNBU_v66_SEMANTIC_Y_UP.glb",
                             "BNBU_v66_RESOLVED_REFERENCES.geojson",
                             "v66_provenance.json"]:
                self.assertTrue((Path(directory) / basename).stat().st_size > 100)


if __name__ == "__main__":
    unittest.main()
