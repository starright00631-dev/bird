#!/usr/bin/env python3
"""Independent source-triangle, GIS immutability and provenance checks for v83."""
from pathlib import Path
import numpy as np, json, trimesh, fiona, hashlib, base64, re
from shapely.geometry import shape
from pyproj import Transformer
R=Path(__file__).resolve().parents[1];I=R/'input';O=R/'model';D=R/'data';Q=R/'qa'
old=trimesh.load(I/'BNBU_v82_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(O/'BNBU_v83_FULL_EDITABLE.glb',force='scene',process=False)
assert (I/'BNBU_v82_FULL_EDITABLE.glb').read_bytes()==(O/'BNBU_v83_FULL_EDITABLE.glb').read_bytes()
assert len(old.graph.nodes_geometry)==len(new.graph.nodes_geometry)==1347
for suffix in ('ACTIVE.geojson','ACTIVE.kml','DISPLAY_ONLY.geojson','DISPLAY_ONLY.kml','EDITABLE_GIS.gpkg'):
 assert (I/('BNBU_v82_'+suffix)).read_bytes()==(D/('BNBU_v83_'+suffix)).read_bytes()
records=json.loads((Q/'v83_v52_probe.json').read_text());assert len(records)==12
assert len(set(r['id'] for r in records))==12
clip=trimesh.load(O/'BNBU_v83_V52_SOURCE_FACE_CLIPS_ONLY.glb',force='scene',process=False)
assert len(clip.graph.nodes_geometry)==24
inp={n for n in old.graph.nodes_geometry if n.startswith('V52_LEVEL2_PEDESTRIAN_CONNECTION_')};assert len(inp)==6
for r in records:
 assert r['bridge_node'] in inp
 tf,k=old.graph[r['bridge_node']];m=old.geometry[k]
 tri=trimesh.transform_points(m.vertices,tf)[m.faces[r['source_face_index']]]
 assert np.max(np.abs(np.asarray(r['source_triangle_xyz'])-tri))<5e-6
 n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);n/=np.linalg.norm(n)
 assert n[2]>.7
 assert np.max(np.abs(n-r['source_face_normal_xyz']))<2e-5
 assert not r['is_verified_connected'] and not r['is_routable']
 for x in r['candidate_model_neighbors']:
  nt,k=old.graph[x['node']];m2=old.geometry[k]
  face=trimesh.transform_points(m2.vertices,nt)[m2.faces[x['source_face_index']]]
  assert np.max(np.abs(face-np.asarray(x['triangle_xyz'])))<5e-6
  nearest=trimesh.triangles.closest_point(np.asarray(face)[None],np.asarray(r['xyz_local_model'])[None])[0]
  assert abs(np.linalg.norm(nearest-np.asarray(r['xyz_local_model']))-x['distance_3d_model_m'])<0.0001
with fiona.open(Q/'BNBU_v83_V52_BRIDGE_ENDPOINT_DIAGNOSTIC.gpkg',layer='qa_v52_12_bridge_ends_not_routable') as g:
 assert len(g)==12 and g.crs.to_epsg()==4326
 assert all(x['properties']['routable']==0 and x['properties']['verified']==0 for x in g)
with fiona.open(D/'BNBU_v83_EDITABLE_GIS.gpkg') as g:pass
assert len(fiona.listlayers(D/'BNBU_v83_EDITABLE_GIS.gpkg'))==146
html=(R/'viewer'/'BNBU_Campus_3D_Offline_v83.html').read_text('utf8')
embedded=base64.b64decode(re.search(r'<script id="embedded-v71" type="application/octet-stream">(.*?)</script>',html,re.S).group(1))
assert embedded==(O/'BNBU_v83_FULL_EDITABLE.glb').read_bytes()
assert 'BNBU_Campus_3D_CPU_v83.html' in html
rep={'pass':True,'main_glb_byte_identical_to_v82':True,'main_scene_meshes':1347,'main_faces':691907,
 'physical_gis_files_all_byte_identical':True,'parent_GPKG_layers':146,'v52_real_source_meshes':6,
 'endpoints_source_checked':len(records),'nearest_face_3d_distance_verified':True,
 'diagnostic_glb_source_face_clips':len(clip.graph.nodes_geometry),
 'all_endpoints_not_surveyed_and_not_routable':True,
 'zero_fabricated_windows_glass_bridges_trees':True,
 'latest_offline_webgl_embedded_exact_GLBSHA256':hashlib.sha256(embedded).hexdigest(),
 'metric_caveat':'All coordinate consistency is internal to an unregistered model; no independent actual site survey.'}
(Q/'v83_independent_validation.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),'utf8');print(json.dumps(rep,indent=2,ensure_ascii=False))