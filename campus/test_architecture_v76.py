"""v76 scientific QA: source mesh preservation, distinct T/V/D/LRC features, GIS environment."""
import hashlib, json, unittest
import numpy as np
from audit_connections_v74 import Surface
from audit_architecture_v76 import (
    build,ATLAS,LINES,GLB,CATS,KEYS,T_KEYS,V_KEYS,D_KEYS,component_group,
    unpack_glb,feature_edges
)

class TestArchitectureV76(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=hashlib.sha256(GLB.read_bytes()).hexdigest()
        cls.report=build()

    def test_original_1379_meshes_not_modified(self):
        self.assertEqual(hashlib.sha256(GLB.read_bytes()).hexdigest(),self.before)
        self.assertEqual(self.report['original_meshes'],1379)
        self.assertTrue(self.report['approach_glb_unchanged'])
        self.assertEqual(self.report['new_campus_triangles'],0)
        self.assertEqual(self.report['new_physical_windows_or_routes'],0)
        self.assertEqual(self.report['new_surveyed_glazing_area'],0)

    def test_30_building_families_preserved(self):
        self.assertEqual(len(self.report['building_records']),30)
        self.assertEqual([x['id'] for x in self.report['building_records']],KEYS)
        self.assertEqual(len(T_KEYS),8)
        self.assertEqual(len(V_KEYS),15)
        self.assertEqual(len(D_KEYS),6)
        for b in self.report['building_records']:
            self.assertTrue(b['no_measured_entry_doors'])
            self.assertTrue(b['no_photo_registered_windows'])
            self.assertTrue(b['not_proof_of_accessible_connection'])
            self.assertEqual(len(b['nearest_walk_or_road']),4)
            self.assertEqual(len(b['nearest_lake']),2)
            self.assertGreater(b['source_plan_area_sq_model_units'],0)
            self.assertTrue(b['existing_component_count']>0)
        self.assertEqual(self.report['families']['LRC']['source_building_count'],1)

    def test_source_mesh_family_classification_not_confused_with_revision(self):
        self.assertEqual(component_group('V34_MODULE_V26_T1_EVIDENCE_BOUNDED_GALLERY_PIER_GROUP__01'),'T')
        self.assertEqual(component_group('V63_RETOPOLOGIZED_OPAQUE_STORYEDGE_V16_1_0'),'V')
        self.assertEqual(component_group('PHASEII_DORM_D1'),'D')
        self.assertEqual(component_group('LRC_DIAGONAL_BRACE_0_0_16'),'LRC')
        self.assertIsNone(component_group('V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE'))

    def test_3d_edges_from_actual_source_vertices(self):
        source=Surface()
        d,binary=unpack_glb(LINES.read_bytes())
        self.assertEqual(len(d['meshes']),4)
        self.assertEqual(len(d['nodes']),4)
        stats=self.report['feature_edge_overlay']
        for k,family in enumerate(CATS):
            mesh=d['meshes'][k]['primitives'][0]
            self.assertEqual(mesh['mode'],1)
            accessor=d['accessors'][mesh['attributes']['POSITION']]
            self.assertEqual(accessor['count']%2,0)
            self.assertEqual(accessor['count']//2,stats[family]['source_sharp_open_edge_segments'])
            self.assertGreater(stats[family]['source_sharp_open_edge_segments'],100)
            view=d['bufferViews'][accessor['bufferView']]
            vertex=np.frombuffer(binary,dtype='<f4',count=accessor['count']*3,
                offset=view.get('byteOffset',0)).reshape(-1,3)
            self.assertTrue(np.isfinite(vertex).all())
            self.assertTrue(d['meshes'][k]['extras']['displayOnly'])
            self.assertFalse(d['nodes'][k]['extras']['bird_collision_area_eligible'])
        # A representative edge may only use vertices on the original mesh.
        edges=feature_edges(source.triangles('LRC_DIAGONAL_BRACE_0_0_16'))
        old=source.triangles('LRC_DIAGONAL_BRACE_0_0_16').reshape(-1,3)
        # Quantized 4-decimal vertices become float32 in the GLB; compare in model units.
        self.assertTrue(all(np.linalg.norm(old-v,axis=1).min()<.00025 for v in edges))

    def test_evidence_does_not_certify_unregistered_facades(self):
        self.assertEqual(self.report['window_panel_count_measured'],None)
        self.assertEqual(self.report['dorm_balcony_number_measured'],None)
        self.assertEqual(self.report['lrc_fins_measured'],None)
        self.assertEqual(len(self.report['published_evidence']),7)
        self.assertTrue(all(s['limits'] for s in self.report['published_evidence']))

    def test_phaseii_inherited_routes_are_classified_without_fabricated_links(self):
        self.assertEqual(self.report['phaseII_route_candidate_count'],14)
        self.assertEqual(self.report['all_route_candidates_count'],70)
        gaps=self.report['phaseII_network_disconnection_audit']
        self.assertEqual(len(gaps),6)
        for k,case in enumerate(gaps,1):
            self.assertEqual(case['dorm'],f'D{k}')
            self.assertGreater(case['dorm_to_radial_plan_gap_model_units'],15)
            self.assertLess(case['dorm_to_radial_plan_gap_model_units'],30)
            self.assertGreater(case['radial_to_central_ring_gap_model_units'],35)
            self.assertLess(case['radial_to_central_ring_gap_model_units'],50)
            self.assertAlmostEqual(case['inferred_connector_to_radial_gap_model_units'],0,places=4)
            self.assertFalse(case['source_model_circulation_verified'])
            self.assertTrue(case['do_not_extrude_missing_paths'])
            for field in ('dorm_to_radial_local_points','radial_to_ring_local_points'):
                p=case[field]
                self.assertEqual(len(p),2)
                self.assertTrue(all(len(x)==3 and all(np.isfinite(v) for v in x) for x in p))
            rec=next(b for b in self.report['building_records'] if b['id']==f'D{k}')
            self.assertGreater(rec['nearest_walk_or_road'][0]['xy_gap_model_units'],600)
            self.assertLess(rec['nearest_approach_candidates'][0]['xy_gap_model_units'],30)
            self.assertTrue(all(not x['physical_connection_verified'] for x in rec['nearest_approach_candidates']))
            self.assertTrue(any(x['source_group']=='phaseII_GLTF_inferred' for x in rec['nearest_approach_candidates']))

    def test_determinism(self):
        old_atlas=ATLAS.read_bytes();old_lines=LINES.read_bytes()
        build()
        self.assertEqual(old_atlas,ATLAS.read_bytes())
        self.assertEqual(old_lines,LINES.read_bytes())

if __name__=='__main__':unittest.main()
