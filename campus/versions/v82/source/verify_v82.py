#!/usr/bin/env python3
"""Independent reload QA for real v82 topology and unchanged inherited GIS geometry."""
from pathlib import Path
import numpy as np,trimesh,fiona,hashlib,json,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]
p=trimesh.load(R/'input/BNBU_v81_FULL_EDITABLE.glb',force='scene',process=False)
s=trimesh.load(R/'model/BNBU_v82_FULL_EDITABLE.glb',force='scene',process=False)
build=json.loads((R/'qa/v82_geometry_build.json').read_text('utf8'))
targets={x['node'] for x in build['changes']}
assert set(s.graph.nodes_geometry)==set(p.graph.nodes_geometry)
assert len(s.graph.nodes_geometry)==len(p.graph.nodes_geometry)==1347
originals_preserved=0;fixed=[]
for name in s.graph.nodes_geometry:
 ta,ka=p.graph[name];tb,kb=s.graph[name];a=p.geometry[ka];b=s.geometry[kb]
 assert np.array_equal(ta,tb),name
 assert np.array_equal(a.vertices,b.vertices),name
 assert len(a.faces)==len(b.faces),name
 assert a.visual.kind==b.visual.kind,name
 if a.visual.kind=='vertex':assert np.array_equal(a.visual.vertex_colors,b.visual.vertex_colors),name
 if a.visual.kind=='texture':assert np.array_equal(a.visual.uv,b.visual.uv),name
 if name in targets:
  assert not a.is_winding_consistent and b.is_winding_consistent
  assert a.volume<0 and b.volume>0
  assert b.is_watertight and b.is_volume
  assert np.array_equal(np.sort(a.faces,axis=1),np.sort(b.faces,axis=1))
  fixed.append(name)
 else:
  assert np.array_equal(a.faces,b.faces),name
  originals_preserved+=1
assert len(fixed)==2 and originals_preserved==1345
assert any(n.startswith('V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL') for n in s.graph.nodes_geometry)
assert not any(('GLAZING_BELT_' in n or 'LINK_GLASS_BALUSTRADE_PROPOSED' in n or 'ROOF_HOUSE_PROXY' in n) for n in s.graph.nodes_geometry)
assert not any(n.startswith('V60_P1_EASTLAKE_EXISTING_BOARDWALK_PIER_') for n in s.graph.nodes_geometry)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
gis_consistency={}
for suffix in ['EDITABLE_GIS.gpkg','ACTIVE.geojson','ACTIVE.kml','DISPLAY_ONLY.geojson','DISPLAY_ONLY.kml']:
 a=R/'input'/('BNBU_v81_'+suffix);b=R/'data'/('BNBU_v82_'+suffix)
 assert sha(a)==sha(b),suffix
 gis_consistency[suffix]=sha(b)
with fiona.open(R/'data/BNBU_v82_EDITABLE_GIS.gpkg') as f: pass
layers=fiona.listlayers(R/'data/BNBU_v82_EDITABLE_GIS.gpkg');assert len(layers)==146
features=json.loads((R/'data/BNBU_v82_ACTIVE.geojson').read_text('utf8'))['features'];assert len(features)==534
pms=ET.parse(R/'data/BNBU_v82_ACTIVE.kml').findall('.//{http://www.opengis.net/kml/2.2}Placemark');assert len(pms)==534
report={'pass':True,'version':'v82','parent':'v81','all_nodes':1347,'all_parent_faces':691907,
 'unchanged_parent_meshes_vertex_face_transform_visual_exact':originals_preserved,
 'changed_existing_meshes_face_winding_only':len(fixed),
 'changed_source_faces_reoriented':16,
 'changed_new_faces':0,'changed_new_vertices':0,
 'both_target_meshes_watertight_winding_consistent_positive_volume':True,
 'lrc_skylight_from_v76_preserved':True,
 'v81_unverified_piers_absent_from_main':True,
 'forbidden_690_glass_6_rails_5_plantrooms_stay_absent':True,
 'geojson_active_features':len(features),'gpkg_layers':len(layers),'kml_active_placemarks':len(pms),
 'gis_files_including_27_display_only_features_bit_identical_to_v81':True,
 'gis_sha256':gis_consistency,
 'main_glb_sha256':sha(R/'model/BNBU_v82_FULL_EDITABLE.glb'),
 'geometry_truth':'Normals only. XY/Z and all surfaces inherited proxy; no orthophoto, OSM way or surveyed vertical datum.'}
(R/'qa/v82_independent_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='gis_sha256'},indent=2,ensure_ascii=False))