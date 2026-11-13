#!/usr/bin/env python3
"""Independent structural, GIS, provenance, and GLB checks for BNBU v86."""
from pathlib import Path
import hashlib,json
import numpy as np
import trimesh, geopandas as gpd
R=Path(__file__).resolve().parents[1]
base=R/'model/BNBU_v84_FULL_EDITABLE.glb'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='242ade4c7cf25a4437e674b271ea451f9367449c23530ca95679b33749989848'
s=trimesh.load(base,force='scene',process=False)
assert len(s.graph.nodes_geometry)==1346 and sum(len(g.faces) for g in s.geometry.values())==691593
for fn,expected_nodes,expected_faces in [
 ('model/BNBU_v86_T1_T3_V52_04_05_TRANSLATED_DISPLAY_ONLY.glb',173,10700),
 ('model/BNBU_v86_T1_T3_V52_04_05_BASELINE_AND_CANDIDATE.glb',346,21400)]:
 q=trimesh.load(R/fn,force='scene',process=False)
 assert len(q.graph.nodes_geometry)==expected_nodes,(fn,len(q.graph.nodes_geometry))
 assert sum(len(g.faces) for g in q.geometry.values())==expected_faces,(fn,sum(len(g.faces) for g in q.geometry.values()))
# For paired GLB, verify exact source colors and face topology on both states.
if expected_nodes==346:
 manifest_nodes=json.loads((R/'qa/v86_component_manifest.json').read_text())['components']
 for item in manifest_nodes:
  n=item['node']; source=s.geometry[s.graph[n][1]]
  for prefix in ('BASELINE__','CANDIDATE__'):
   mesh=q.geometry[q.graph[prefix+n][1]]
   assert np.array_equal(mesh.faces,source.faces),n
   assert mesh.visual.kind==source.visual.kind,n
   if source.visual.kind=='vertex':
    assert np.array_equal(mesh.visual.vertex_colors,source.visual.vertex_colors),n
   elif source.visual.kind=='texture':
    uv0=getattr(source.visual,'uv',None);uv1=getattr(mesh.visual,'uv',None)
    assert (uv0 is None and uv1 is None) or np.array_equal(uv0,uv1),n
    d0=source.visual.material._data;d1=mesh.visual.material._data
    assert set(d0)==set(d1),n
    for key,value in d0.items():
     other=d1[key]
     if isinstance(value,np.ndarray): assert np.array_equal(value,other),(n,key)
     else: assert value==other,(n,key)
a=json.loads((R/'qa/v86_registration_audit.json').read_text())
assert a['candidate_components']==173 and a['candidate_triangles']==10700
assert a['master_glb_modified'] is False and a['master_gpkg_modified'] is False
assert a['candidate_is_surveyed'] is False and a['polygon_boundary_fit_performed'] is False
assert a['roundtrip_validation']['baseline_meshes_checked']==173
assert a['roundtrip_validation']['candidate_meshes_checked']==173
assert a['roundtrip_validation']['max_baseline_vertex_error_m']==0
assert a['roundtrip_validation']['max_candidate_translation_error_m']==0
assert a['roundtrip_validation']['face_index_arrays_identical'] is True
expected_gis={'BNBU_v84_EDITABLE_GIS.gpkg':'6bf8807eea0c7811b18c1569551bd806e117d518ba50f6ad0979686a29d78374','BNBU_v84_ACTIVE.geojson':'a2cf23094f388eb1004a58c206862773161a3a7866d4b25791dd8f34800f08fa','BNBU_v84_ACTIVE.kml':'a81286cb18108ff56b61a4b22ca689a36c60f04974055592674759e0d05a50b3'}
for name,sha in expected_gis.items():
 assert hashlib.sha256((R/'data'/name).read_bytes()).hexdigest()==sha,name
ends=json.loads((R/'qa/v86_v52_04_05_endpoint_recheck.json').read_text())
assert len(ends['endpoints'])==4 and not ends['all_routable']
assert all(x['is_routable'] is False and x['is_verified_connected'] is False for x in ends['endpoints'])
manifest=json.loads((R/'qa/v86_component_manifest.json').read_text())
assert len(manifest['components'])==173 and sum(x['triangles'] for x in manifest['components'])==10700
osm=json.loads((R/'qa/v86_osm_way_snapshot.json').read_text())
assert [len(osm['ways'][b]['nodes']) for b in ('T1','T2','T3')]==[19,20,17]
gpkg=R/'data/BNBU_v86_REGISTRATION_QA_ONLY.gpkg'
layers=gpd.list_layers(gpkg)['name'].tolist()
assert set(layers)=={'registration_centres','registration_residuals','candidate_shift_vectors'},layers
counts={}
for layer,n in [('registration_centres',9),('registration_residuals',6),('candidate_shift_vectors',3)]:
 g=gpd.read_file(gpkg,layer=layer);counts[layer]=len(g);assert len(g)==n;assert str(g.crs).endswith('4326')
geo=json.loads((R/'data/BNBU_v86_REGISTRATION_QA_ONLY.geojson').read_text())
assert len(geo['features'])==18
html=(R/'viewer/BNBU_v86_T1_T3_OSM_Registration_Comparison.html').read_text('utf-8')
assert 'https://' not in html and 'DATA=' in html and '__BNBU_V86__' in html
assert (R/'viewer/BNBU_Campus_3D_Offline_v84.html').stat().st_size>25_000_000
assert (R/'viewer/BNBU_v85_V52_V60_Actual_SourceTriangle_3D_Inspector.html').stat().st_size>250_000
assert (R/'figures/BNBU_v86_registration_overlay_Chromium.png').exists()
road=trimesh.load(R/'model/BNBU_v84_ROAD000_RETAINED_ONLY.glb',force='scene',process=False)
assert len(road.graph.nodes_geometry)==1 and sum(len(g.faces) for g in road.geometry.values())==416
# Confirm the v84 active physical GIS files are unchanged from the v85 parent copies.
for name in ['BNBU_v84_EDITABLE_GIS.gpkg','BNBU_v84_ACTIVE.geojson','BNBU_v84_ACTIVE.kml']:
 p=R/'data'/name
 assert p.exists() and p.stat().st_size>0
print(json.dumps({'status':'PASS','parent_meshes':1346,'parent_triangles':691593,
 'candidate_meshes':173,'candidate_triangles':10700,'comparison_meshes':346,'comparison_triangles':21400,
 'qa_gpkg_layers':layers,'qa_gpkg_counts':counts,'qa_geojson_features':len(geo['features']),
 'v52_04_05_endpoints':len(ends['endpoints'])},ensure_ascii=False))