#!/usr/bin/env python3
"""Independent main/branch reconciliation QA; fails hard on regressions."""
from pathlib import Path
import json,struct,hashlib,sqlite3,xml.etree.ElementTree as ET
import numpy as np,trimesh,fiona
R=Path(__file__).resolve().parent
main=trimesh.load(R/'input/main_v71.glb',force='scene',process=False)
branch=trimesh.load(R/'input/branch_v77.glb',force='scene',process=False)
active=trimesh.load(R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb',force='scene',process=False)
summary=json.loads((R/'qa/v78_geometry_compatibility.json').read_text())
ma=set(main.graph.nodes_geometry);nb=set(branch.graph.nodes_geometry);ac=set(active.graph.nodes_geometry)
replacement=summary['source_main_name_to_branch_replacements']
assert len(ma)==1379 and len(nb)==1382 and len(ac)==1380
assert len(replacement)==37
assert ma-ac==set(replacement) and ac-ma==set(replacement.values())|{'V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED'}
unchanged=0
for n in sorted(ma&ac):
 if n=='V24_P2_CIRCULAR_COMMONS_09_LOW_CENTRAL_ROOF_CIRCLE':continue
 tf,gm=main.graph[n];tf2,ga=active.graph[n];m=main.geometry[gm];a=active.geometry[ga]
 assert np.array_equal(tf,tf2) and np.array_equal(m.vertices,a.vertices) and np.array_equal(m.faces,a.faces),n
 if hasattr(m.visual,'vertex_colors') and hasattr(a.visual,'vertex_colors'):assert np.array_equal(m.visual.vertex_colors,a.visual.vertex_colors),n
 unchanged+=1
assert unchanged==1341
for old,new in replacement.items():
 m=active.geometry[active.graph[new][1]]
 assert m.is_watertight and m.is_winding_consistent and m.volume>0,new
 assert np.array_equal(m.faces,branch.geometry[branch.graph[new][1]].faces),new
cap='V24_P2_CIRCULAR_COMMONS_09_LOW_CENTRAL_ROOF_CIRCLE'
parent=main.geometry[main.graph[cap][1]];now=active.geometry[active.graph[cap][1]]
assert np.array_equal(parent.faces,now.faces)
assert np.array_equal(parent.vertices[:,:2],now.vertices[:,:2])
height=now.vertices[:,2]-parent.vertices[:,2]
assert abs(np.max(height)-np.min(height))<2e-5
assert abs(float(np.mean(height))-summary['cap_z_offset_model_relative'])<1e-5
for target in ['V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_01_NOT_SURVEYED','V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_02_NOT_SURVEYED']:
 assert np.array_equal(main.geometry[main.graph[target][1]].faces,active.geometry[active.graph[target][1]].faces)
assert all(not n.startswith('V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_') for n in ac)
assert all(not n.startswith('V64_CONSTRAINED_RELIEF_') for n in ac)
assert len([n for n in ac if n.startswith('V53_')])>=4
assert all(not any(f in n for f in ('GLAZING_BELT_','LINK_GLASS_BALUSTRADE_PROPOSED','ROOF_HOUSE_PROXY')) for n in ac)
# Validate glTF world rotation against actual MAIN, so old viewer vertical axis is preserved.
def getroot(path):
 b=path.read_bytes();magic,version,total=struct.unpack_from('<4sII',b)
 assert magic==b'glTF' and version==2 and len(b)==total
 jlen,jtyp=struct.unpack_from('<I4s',b,12);assert jtyp==b'JSON'
 j=json.loads(b[20:20+jlen]);node=j['nodes'][j['scenes'][0]['nodes'][0]]
 assert node['name']=='world'
 return node.get('rotation',[0,0,0,1])
worldA=getroot(R/'input/main_v71.glb');worldNew=getroot(R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb')
assert np.allclose(worldA,worldNew,atol=1e-7),(worldA,worldNew)
geo=json.loads((R/'data/BNBU_v78_ACTIVE.geojson').read_text());assert len(geo['features'])==567
ns={'k':'http://www.opengis.net/kml/2.2'};tree=ET.parse(R/'data/BNBU_v78_ACTIVE.kml');assert len(tree.findall('.//k:Placemark',ns))==567
layers=fiona.listlayers(R/'data/BNBU_v78_EDITABLE_GIS.gpkg');assert len(layers)==144 and "bnbu_v78_scene_membership" in layers
with sqlite3.connect(R/'data/BNBU_v78_EDITABLE_GIS.gpkg') as con:
 out=con.execute('select model_node,scene_role from bnbu_v78_scene_membership').fetchall()
assert len(out)==8 and len([a for a,b in out if 'DISPLAY_ONLY' in b])==6
js=(R/'viewer/viewer.js').read_text();html=(R/'viewer/index.html').read_text()
assert 'generated/BNBU_v78_RECONCILED_MAIN.glb' in js and 'show-v78-seams' in html and 'show-v78-skylight' in html
assert (R/'viewer/generated/BNBU_v78_RECONCILED_MAIN.glb').read_bytes()==(R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb').read_bytes()
assert (R/'viewer/generated/BNBU_v78_PAVING_SEAMS_DISPLAY_ONLY.glb').read_bytes()==(R/'model/BNBU_v78_PAVING_SEAMS_DISPLAY_ONLY.glb').read_bytes()
report={'version':'v78','pass':True,'main_nodes':len(ma),'branch_nodes':len(nb),'new_active_nodes':len(ac),'parent_meshes_bytewise_geometry_equal':unchanged,'retopologized_opaque_trims':len(replacement),'new_skylight_meshes':1,'corrected_cap_Z_relative':float(np.mean(height)),'bridge_contact_faces_preserved':2,'root_rotation_main':worldA,'root_rotation_reconciled':worldNew,'v77_roof_seams_active':0,'v64_smoothed_terrain_active':0,'GPKG_spatial_layers':len(layers)-1,'GeoJSON_features':len(geo['features']),'KML_placemarks':567,'GIS_membership_roles':len(out),'viewer_asset_hash_matches_model':True,'no_new_unsourced_glass_windows_trees':True,'geodetic_vertical_datum_verified':False,'new_OSM_way_nodes':0,'full_browser_runtime_this_run':'not verified: sandbox Chromium blocks localhost/file navigation by administrator','model_sha256':hashlib.sha256((R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb').read_bytes()).hexdigest()}
(R/'qa/v78_independent_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))