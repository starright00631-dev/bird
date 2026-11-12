"""v71 source-bound construction contract, no new roads or unsurveyed bridge geometry."""
import json,unittest
from shapely.geometry import shape
from shapely.ops import transform
from build_connection_v71 import build,unpack,BASE,OUT,PATCH,GRAPH,GIS,CONTROL,TO_UTM

class TestV71(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.meta=build()
  cls.before,cls.b0=unpack(BASE.read_bytes())
  cls.after,cls.b1=unpack(OUT.read_bytes())
  cls.features=json.loads(PATCH.read_text())["features"]
  cls.graph=json.loads(GRAPH.read_text())["features"]
  cls.gis=json.loads(GIS.read_text())["features"]
 def test_existing_geometry_preserved_byte_exact(self):
  self.assertEqual(len(self.before["meshes"]),1377)
  self.assertEqual(len(self.after["meshes"]),1379)
  self.assertEqual(self.before["meshes"],self.after["meshes"][:1377])
  self.assertEqual(self.before["accessors"],self.after["accessors"][:len(self.before["accessors"])])
  self.assertEqual(self.b0,self.b1[:len(self.b0)])
  self.assertEqual(len(self.gis),522)
  self.assertEqual(self.meta["source_mesh_binary_sha256"],self.meta["result_binary_original_prefix_sha256"])
 def test_two_land_only_grade_matched_small_patches(self):
  self.assertEqual(len(self.features),2)
  control=json.loads(CONTROL.read_text())
  self.assertEqual(len(control["features"]),2)
  originals={}
  for f in self.gis:
   n=f["properties"].get("render_model_node") or f["properties"].get("model_node")
   if n:originals.setdefault(n,[]).append(transform(TO_UTM,shape(f["geometry"])))
  get=lambda n:max(originals[n],key=lambda g:g.area)
  lake=get("LAKE_00")
  for f in self.features:
   p=f["properties"];poly=transform(TO_UTM,shape(f["geometry"]))
   self.assertTrue(3<poly.area<6)
   self.assertLess(poly.intersection(lake.buffer(.35)).area,1e-6)
   self.assertLess(poly.distance(get(p["source_a"])),.12)
   self.assertLess(poly.distance(get(p["source_b"])),.12)
   self.assertAlmostEqual(p["model_top_z"],.27,delta=.01)
   self.assertFalse(p["is_surveyed"])
   self.assertFalse(p["metric_birdstrike_eligible"])
 def test_graph_does_not_invent_road_or_bridge(self):
  self.assertEqual(len(self.graph),11)
  statuses=[g["properties"]["junction_status"] for g in self.graph]
  self.assertEqual(statuses.count("model_derived_pavement_join_added"),2)
  self.assertEqual(statuses.count("vertical_mismatch_unresolved"),3)
  self.assertEqual(statuses.count("do_not_bridge_lake"),1)
  self.assertEqual(statuses.count("existing_road_to_path_seam"),1)
  self.assertEqual(len(self.meta["second_floor_walkways_are_not_road_bridges"]),6)
  self.assertTrue(all(f["properties"]["needs_photogrammetry"] for f in self.graph))

if __name__=="__main__":unittest.main()
