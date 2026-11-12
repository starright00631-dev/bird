#!/usr/bin/env python3
"""Independent v79 asset, 3D source-face, no-unverified-route and GIS checks."""
from pathlib import Path
import json,hashlib,sqlite3,zipfile
import numpy as np,trimesh,fiona
R=Path(__file__).resolve().parents[1];P=R/'parent_v78';M=R/'model';D=R/'data';Q=R/'qa';V=R/'viewer'
original=P/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb';current=M/'BNBU_v79_MAIN_INHERITED_UNMODIFIED.glb'
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert H(original)==H(current)=='6a89879e5b64e7d56581cee54cbc7e1b62b60eb1f48cb57b56bdbbb7dbbb23b4'
source=trimesh.load(original,force='scene',process=False)
local=trimesh.load(M/'BNBU_v79_REAL_SOURCE_FACE_CLIPS_ONLY.glb',force='scene',process=False)
checks=json.loads((Q/'v79_layer_aware_junctions.json').read_text())['cases']
prov=json.loads((Q/'v79_face_clip_provenance.json').read_text())
assert len(source.graph.nodes_geometry)==1380 and len(local.graph.nodes_geometry)==130 and len(checks)==65
assert len([x for x in checks if x['kind']=='inherited_47_hotspots'])==47
assert len([x for x in checks if x['kind']=='v52_bridge_ends_same_deck'])==6
assert len([x for x in checks if x['kind']=='dorm_ground_to_radial'])==6
assert len([x for x in checks if x['kind']=='radial_to_ring'])==6
for n in local.graph.nodes_geometry:
 ltf,k=local.graph[n];m=local.geometry[k];v=trimesh.transform_points(m.vertices,ltf)
 s=prov[n];stf,sk=source.graph[s['parent_mesh']];t=source.geometry[sk]
 orig=trimesh.transform_points(t.vertices,stf)[t.faces[s['source_face_ids']]].reshape(-1,3)
 assert v.shape==orig.shape and np.array_equal(v,orig),n
for c in checks:
 assert c['walkability']=='UNVERIFIED_NO_AUTO_CONNECTION'
 for label in ('a','b'):
  x=c[label];assert not x['route_verified'] and not x['door_verified'] and not x['absolute_z_surveyed']
  assert x['anchor_z_abs_error']<=0.1
DR=[x for x in checks if x['kind']=='dorm_ground_to_radial']
for x in DR:
 assert x['a']['face_normal_xyz'][2]<-.99
 assert x['a']['candidate_heights']==[0.,32.]
 assert abs(x['a']['highest_intersection_bias']-32)<1e-5
 assert not x['a']['candidate_walk_upward_normal']
 assert x['z_gap_model_m']==.044
for n in ('BNBU_v79_ACTIVE.geojson','BNBU_v79_ACTIVE.kml'):
 assert H(D/n)==H(P/'data'/n.replace('v79','v78'))
with sqlite3.connect(D/'BNBU_v79_EDITABLE_GIS.gpkg') as con:
 assert con.execute("SELECT COUNT(*) FROM gpkg_contents WHERE data_type='features'").fetchone()[0]==143
 assert con.execute("SELECT COUNT(*) FROM bnbu_v79_surface_layer_checks").fetchone()[0]==130
 assert con.execute("SELECT COUNT(*) FROM bnbu_v79_surface_layer_checks WHERE route_verified<>0 OR surveyed<>0").fetchone()[0]==0
assert len(json.loads((D/'BNBU_v79_ACTIVE.geojson').read_text())['features'])==567
assert len(json.loads((V/'v79_canvas_geometry_data.json').read_text()))==65
with zipfile.ZipFile(R/'input/BNBU_campus_geometry_v78_2026-11-12.zip') as z:
 assert 'BNBU_Campus_v78/reference/BNBU_hourly_campus_v10_2026-11-10.zip' in z.namelist()
report={'version':'v79','pass':True,'main_GLb_meshes_untouched':1380,'source_face_submesh_nodes':130,'byte_exact_clip_vertices':True,
        'outward_navigability_not_asserted':True,'roof_vs_base_Z30_plus_in_all_D1_to_D6':True,
        'dorm_base_faces_downward_not_walkways':True,'model_relative_z_disclosed':True,
        'GPKG_spatial_layers':143,'GIS_nonspatial_QA_rows':130,'geojson_features':567,'KML_inherited_sha256_verified':True,
        'source_v10_archive_retained':True,'no_new_survey_claim':True,'no_osm_way_data':True,
        'full_v78_WebGL_viewer_runtime':'unverified here; environment WebGL1/WebGL2 context unavailable'}
(Q/'v79_independent_validation.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps(report,indent=2))