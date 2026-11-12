"""Evidence and geometry gates for source-anchored v75 bridge research."""
import hashlib,json,unittest
import numpy as np
from build_bridges_v75 import build,GLB,GLASS,ATLAS,RAILS,unpack_glb,NODE

class TestBridge75(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=hashlib.sha256(GLB.read_bytes()).hexdigest()
        cls.data=build()
        cls.doc,cls.binary=unpack_glb(GLASS.read_bytes())

    def test_inherited_campus_mesh_is_unchanged(self):
        self.assertEqual(self.before,hashlib.sha256(GLB.read_bytes()).hexdigest())
        self.assertFalse(self.data['source_glb_modified'])
        self.assertFalse(self.data['gates']['scientific_mesh_modified'])
        self.assertFalse(self.data['gates']['bird_collision_input_added'])
        self.assertFalse(self.data['gates']['assume_V52_glazing'])
        self.assertFalse(self.data['v60_lakefront_boardwalk']['glass_denominator_eligible'])

    def test_glass_strip_anchored_to_source_340_points(self):
        a=self.doc['accessors'];v=self.doc['bufferViews'];binary=self.binary
        xyz=np.frombuffer(binary,dtype='<f4',count=a[0]['count']*3,offset=v[0]['byteOffset']).reshape(-1,3)
        ind=np.frombuffer(binary,dtype='<u4',count=a[1]['count'],offset=v[1]['byteOffset'])
        src=np.asarray(json.loads(RAILS.read_text())['railing_xy_polylines_local'][0])
        self.assertEqual(src.shape,(340,3))
        self.assertEqual(xyz.shape,(1356,3))
        self.assertEqual(len(ind),2034)
        self.assertTrue(np.isfinite(xyz).all())
        self.assertAlmostEqual(float(xyz[:,2].min()),float(src[:,2].min()+.1),places=3)
        self.assertAlmostEqual(float(xyz[:,2].max()),float(src[:,2].max()+.8),places=3)
        self.assertTrue(all(np.linalg.norm(src[:,:2]-p,axis=1).min()<.002 for p in xyz[:,:2]))
        self.assertEqual(self.doc['nodes'][0]['name'],NODE)
        self.assertEqual(self.doc['materials'][0]['alphaMode'],'BLEND')
        self.assertEqual(self.doc['meshes'][0]['extras']['bird_glass_exposure_eligible'],False)
        self.assertEqual(self.data['v75_glass_infill']['glass_panel_count_verified'],None)
        self.assertEqual(self.data['v75_glass_infill']['real_glass_surface_area_verified'],None)

    def test_six_links_are_12_distinct_interfaces(self):
        bridges=self.data['v52_elevated_academic_bridges']
        self.assertEqual(len(bridges),6)
        end_pairs={
            'V52_00':['T4','T5'],'V52_01':['T6','T5'],
            'V52_02':['T7','T6'],'V52_03':['T8','T7'],
            'V52_04':['T1','T2'],'V52_05':['T3','T2']}
        for bridge in bridges:
            self.assertEqual([e['linked_building_candidate'] for e in bridge['endpoints']],end_pairs[bridge['id']])
            self.assertTrue(all(e['surface_covered'] for e in bridge['endpoints']))
            self.assertTrue(all(not e['threshold_passable_verified'] for e in bridge['endpoints']))
            self.assertTrue(bridge['endpoint_assignment_revalidated_from_source_building_envelopes'])
            self.assertFalse(bridge['glazed_facade_mesh_created'])
        curved=next(b for b in bridges if b['id']=='V52_03')
        ends=[e['model_top_height_m'] for e in curved['endpoints']]
        self.assertGreater(ends[1]-ends[0],.5)

    def test_13_piers_and_source_photo_gates(self):
        self.assertEqual(self.data['v60_lakefront_boardwalk']['source_pier_model_count'],13)
        self.assertEqual(self.data['v60_lakefront_boardwalk']['source_opaque_crossbeam_model_count'],13)
        photos=self.data['photo_and_design_source_register']
        self.assertGreaterEqual(len(photos),8)
        self.assertEqual(len({x['url'] for x in photos}),len(photos))
        self.assertTrue(all(x['limits'] for x in photos))
        self.assertEqual(self.data['v74_junction_hotspot_count_preserved'],47)

    def test_deterministic_outputs(self):
        before_glb=GLASS.read_bytes();before_atlas=ATLAS.read_bytes()
        build()
        self.assertEqual(before_glb,GLASS.read_bytes())
        self.assertEqual(before_atlas,ATLAS.read_bytes())

if __name__=='__main__': unittest.main()
