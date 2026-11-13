#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, hashlib, trimesh, fiona, xml.etree.ElementTree as ET, re, base64
R=Path(__file__).resolve().parents[1]
old=trimesh.load(R/'input/BNBU_v83_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(R/'model/BNBU_v84_FULL_EDITABLE.glb',force='scene',process=False)
arc=trimesh.load(R/'model/BNBU_v84_REDUNDANT_ROAD000_SIDE_DISPLAY_ONLY.glb',force='scene',process=False)
a=set(old.graph.nodes_geometry);b=set(new.graph.nodes_geometry)
removed='V42_FACET_SIDE_ROAD_000'; retained='ROAD_000'
assert a-b=={removed} and b-a==set()
assert len(b)==1346 and set(arc.graph.nodes_geometry)=={removed}
old_faces=sum(len(g.faces) for g in old.geometry.values());new_faces=sum(len(g.faces) for g in new.geometry.values())
assert old_faces==691907 and new_faces==691593
assert old.graph.base_frame==new.graph.base_frame
for n in b:
 ta,ka=old.graph[n];tb,kb=new.graph[n]
 ma=old.geometry[ka];mb=new.geometry[kb]
 assert np.array_equal(ta,tb),n
 assert np.array_equal(ma.faces,mb.faces),n
 assert np.array_equal(ma.vertices,mb.vertices),n
 assert ma.visual.kind==mb.visual.kind,(n,ma.visual.kind,mb.visual.kind)
 if ma.visual.kind=='vertex':
  assert np.array_equal(ma.visual.vertex_colors,mb.visual.vertex_colors),n
 elif ma.visual.kind=='face':
  assert np.array_equal(ma.visual.face_colors,mb.visual.face_colors),n
 elif ma.visual.kind=='texture':
  assert np.array_equal(ma.visual.uv,mb.visual.uv),n
  for attr in ('baseColorFactor','metallicFactor','roughnessFactor','alphaMode'):
   if hasattr(ma.visual.material,attr):
    assert str(getattr(ma.visual.material,attr))==str(getattr(mb.visual.material,attr)),(n,attr)
n=removed
assert np.array_equal(arc.geometry[arc.graph[n][1]].vertices,old.geometry[old.graph[n][1]].vertices)
assert np.array_equal(arc.geometry[arc.graph[n][1]].faces,old.geometry[old.graph[n][1]].faces)
assert len(new.geometry[new.graph[retained][1]].faces)==416
# Original skylight is present and unchanged.
sky='V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED'
assert sky in b and len(new.geometry[new.graph[sky][1]].faces)==34816
# All six V52 bridge meshes are unchanged and 12 original source face references persist.
probes=json.loads((R/'reference/v83_v52_probe.json').read_text())
assert len(probes)==12
for p in probes:
 bridge=p['bridge_node'];tri=new.geometry[new.graph[bridge][1]].triangles[p['source_face_index']]
 assert np.allclose(tri,np.array(p['source_triangle_xyz']),atol=2e-5)
 assert p['is_routable'] is False and p['is_verified_connected'] is False
for base in ['EDITABLE_GIS.gpkg','ACTIVE.geojson','ACTIVE.kml']:
 assert (R/f'input/BNBU_v83_{base}').read_bytes()==(R/f'data/BNBU_v84_{base}').read_bytes()
assert len(fiona.listlayers(R/'data/BNBU_v84_EDITABLE_GIS.gpkg'))==146
fc=json.loads((R/'data/BNBU_v84_ACTIVE.geojson').read_text());assert len(fc['features'])==534
nms={p['properties'].get('model_node') for p in fc['features']}
assert removed not in nms and retained in nms
root=ET.parse(R/'data/BNBU_v84_ACTIVE.kml');assert len(root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'))==534
full=(R/'viewer/BNBU_Campus_3D_Offline_v84.html').read_text()
assert 'it.length!==1346' in full and 'it.length!==1380' not in full
assert 'href="#cpu-fallback" id="bn-cpu-fallback"' in full
assert 'BNBU_Campus_3D_CPU_v83.html' not in full
m=re.search(r'<script id="embedded-v71" type="application/octet-stream">(.*?)</script>',full,re.S)
assert m and base64.b64decode(m.group(1))==(R/'model/BNBU_v84_FULL_EDITABLE.glb').read_bytes()
assert base64.b64decode(re.search(r'<script id="embedded-cpu-v84" type="application/octet-stream">(.*?)</script>',full,re.S).group(1))==(R/'viewer/BNBU_Campus_3D_CPU_v84.html').read_bytes()
report={'result':'PASS','version':'v84','main_nodes':len(b),'main_source_faces':new_faces,'unchanged_nodes_exact_vertices_faces_transforms_colors':len(b),'removed_geometry_overlay_faces':314,'ROAD_000_retained_faces':416,'sky_faces_unchanged':34816,'v52_verified_source_faces_unchanged':12,'GPKG_layers':146,'geojson_features':534,'kml_placemarks':534,'viewer_webgl_guard_corrected':True,'viewer_main_GLBSHA256_embedded':hashlib.sha256((R/'model/BNBU_v84_FULL_EDITABLE.glb').read_bytes()).hexdigest(),'CPU_fallback_embedded_identical_to_sidecar':True,'measurement_qualified_new_geometry':0,'no_new_windows_routes_trees_roof_machinery':True}
(R/'qa/v84_independent_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report,ensure_ascii=False,indent=2))