"""v72: cross-check source 3D elevation profiles and 16 unique BNBU images."""
import hashlib,json,unittest
from build_connection_profiles_v72 import build,OUTPUT,MODEL,GIS,PHOTOS

class TestV72(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=build()
 def test_true_source_xyz_and_unmodified_model(self):
  d=self.data
  self.assertEqual(d["scene_glb_sha256"],hashlib.sha256(MODEL.read_bytes()).hexdigest())
  self.assertEqual(d["source_gis_sha256"],hashlib.sha256(GIS.read_bytes()).hexdigest())
  self.assertEqual((d["original_source_meshes"],d["v71_scene_meshes"],d["source_gis_features"]),(1377,1379,522))
  self.assertEqual((d["physically_new_road_meshes"],d["physically_new_bridge_meshes"],d["physically_new_stair_meshes"]),(0,0,0))
  self.assertEqual(json.loads(OUTPUT.read_text()),d)
 def test_both_ramp_edges_actually_slope_to_land(self):
  ramp=[x for x in self.data["rail_profiles"] if x["category"]=="bridge_to_land_slope"]
  self.assertEqual(len(ramp),2)
  for p in ramp:
   pts=p["model_surface_xyz"]
   self.assertGreater(len(pts),35)
   self.assertGreater(pts[0][2],pts[-1][2]+.66)
   self.assertGreater(pts[0][2],.7)
   self.assertLess(pts[-1][2],.25)
   self.assertTrue(all(317<=xyz[0]<=340 and -103<=xyz[1]<=-88 for xyz in pts))
   self.assertTrue(p["guardrail_height_is_not_surveyed"])
 def test_lrc_stair_rails_follow_19_existing_levels(self):
  stairs=[x for x in self.data["rail_profiles"] if x["category"]=="building_to_ground_stair"]
  self.assertEqual(len(stairs),2)
  for p in stairs:
   pts=p["model_surface_xyz"]
   self.assertEqual(len(pts),19)
   self.assertAlmostEqual(pts[0][2],.172,delta=.003)
   self.assertAlmostEqual(pts[-1][2],3.10,delta=.003)
   self.assertTrue(all(130.9<=x<=135.2 and -53.5<=y<=-38.5 for x,y,z in pts))
   self.assertLess(max(b[2]-a[2] for a,b in zip(pts,pts[1:])),.18)
 def test_all_unresolved_grade_differences_preserved(self):
  markers=self.data["height_disagreement_markers"]
  self.assertEqual(len(markers),3)
  self.assertEqual(sorted(round(x["delta"],2) for x in markers),[.24,.64,.64])
  self.assertTrue(all("NOT A CONNECTOR" in x["status"] for x in markers))
 def test_photo_metadata_valid_sources_and_no_chicago(self):
  cat=json.loads(PHOTOS.read_text())
  self.assertEqual(cat["observed_distinct_photos"],16)
  urls=[x["image_url"] for x in cat["photos"]]
  self.assertEqual(len(set(urls)),16)
  self.assertTrue(all(x["image_url"].startswith("https://") and x["source_url"].startswith("https://") for x in cat["photos"]))
  self.assertTrue(all(x["visual_use_only"] and not x["can_locate_xy"] and not x["can_measure_z"] for x in cat["photos"]))
  self.assertIn("NOT University of Illinois",cat["campus"])
  self.assertTrue(self.data["no_glass_birdstrike_metric_area"])

if __name__=="__main__":unittest.main()
