"""Regression tests for v74 local junction-grade analysis and evidence gates."""
import hashlib,json,unittest
from audit_connections_v74 import build,Surface,GIS,GLB,OLD,PAIR_OUTPUT,HOTSPOT_OUTPUT,REPORT_OUTPUT
from build_connection_v71 import DECK,RAMP,S

class V74JunctionResearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=[hashlib.sha256(p.read_bytes()).digest() for p in (GLB,GIS,OLD)]
        cls.summary=build()
        cls.audit=json.loads(HOTSPOT_OUTPUT.read_text())
        cls.pairs=json.loads(PAIR_OUTPUT.read_text())

    def test_all_1540_road_footpath_pairs_preserved(self):
        self.assertEqual(self.summary['total_pairwise_comparisons'],1540)
        self.assertEqual(len(self.pairs['pairs']),1540)
        self.assertGreaterEqual(len(self.audit['features']),41)
        self.assertEqual(self.summary['upper_level_cross_checks'],336)
        self.assertEqual(len(self.pairs['upper_level_pairs']),336)
        self.assertEqual(self.summary['count_by_type']['within_3'],9)
        self.assertEqual(self.summary['count_by_type']['overlap_over_10m2'],2)
        self.assertEqual(len({(x['source_a'],x['source_b']) for x in self.pairs['pairs']}),1540)

    def test_local_grade_not_whole_mesh_maximum(self):
        hot=self.audit['features']
        def lookup(a,b):
            return next(x['properties'] for x in hot if x['properties']['source_a']==a and x['properties']['source_b']==b)
        east=lookup(RAMP,'WALK_044')
        self.assertTrue(east['both_projected_to_source_triangles'])
        self.assertLess(east['local_top_delta_m'],.06)
        self.assertGreater(east['whole_mesh_top_delta_m'],.85)
        self.assertGreater(east['whole_mesh_top_delta_m']-east['local_top_delta_m'],.80)
        deckramp=lookup(DECK,RAMP)
        self.assertLess(deckramp['local_top_delta_m'],.08)
        west=lookup(DECK,S[2])
        self.assertAlmostEqual(west['local_top_delta_m'],.64,places=3)
        self.assertTrue(west['both_projected_to_source_triangles'])

    def test_no_false_physical_links(self):
        for item in self.audit['features']:
            p=item['properties']
            self.assertFalse(p['is_surveyed'])
            self.assertTrue(p['do_not_extrude_as_walkway'])
            self.assertFalse(p['navigation_connection_proven'])
            self.assertEqual(len(p['local_points_z_up']),2)
            self.assertIn(p['local_surface_method_a'],['barycentric_triangle_surface','uncovered_nearest_vertex'])
            self.assertIn(p['local_surface_method_b'],['barycentric_triangle_surface','uncovered_nearest_vertex'])
        self.assertEqual(self.summary['campus_3d_meshes_edited'],0)
        self.assertEqual(self.summary['newsurveyed_links'],0)

    def test_input_hashes_unchanged(self):
        after=[hashlib.sha256(p.read_bytes()).digest() for p in (GLB,GIS,OLD)]
        self.assertEqual(after,self.before)
        self.assertEqual(self.summary['inputs']['GLB_v71_sha256'],hashlib.sha256(GLB.read_bytes()).hexdigest())
        self.assertEqual(self.summary['inputs']['GIS_v66_sha256'],hashlib.sha256(GIS.read_bytes()).hexdigest())

    def test_repeatable_output(self):
        old=[hashlib.sha256(p.read_bytes()).digest() for p in (PAIR_OUTPUT,HOTSPOT_OUTPUT,REPORT_OUTPUT)]
        build()
        self.assertEqual(old,[hashlib.sha256(p.read_bytes()).digest() for p in (PAIR_OUTPUT,HOTSPOT_OUTPUT,REPORT_OUTPUT)])

if __name__=='__main__':unittest.main()