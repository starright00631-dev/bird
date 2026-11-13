#!/usr/bin/env python3
"""Evidence-bounded main v76.1 + v77 geometry reconciliation (not version-string concatenation).

Main v71 GLB is the immutable reference for 47 hotspots / 30 building source views.
Only 37 verified opaque trims are replaced, one inherited pavilion cap is corrected
at unchanged XY, and one skylight is added at inherited rim. Unregistered seam and
terrain-smoothing alternates are quarantined as DISPLAY_ONLY. Nothing guessed is
added to surveyed roads, bird glass denominators, or geodetic vertical heights.
"""
from pathlib import Path
import trimesh, numpy as np, json, fiona, sqlite3, shutil, hashlib, struct, xml.etree.ElementTree as ET
from shapely.geometry import Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent
MAIN=ROOT/'input/main_v71.glb'; BRANCH=ROOT/'input/branch_v77.glb'
MD=ROOT/'model';D=ROOT/'data';QA=ROOT/'qa'
for p in [MD,D,QA]:p.mkdir(parents=True,exist_ok=True)
A=trimesh.load(MAIN,force='scene',process=False);B=trimesh.load(BRANCH,force='scene',process=False)
ma=set(A.graph.nodes_geometry); mb=set(B.graph.nodes_geometry)
assert len(ma)==1379 and len(mb)==1382
old=[n for n in ma if n.startswith('FLOOR_EDGE_NOT_GLASS_STORYBAND_') and ('_'+n.split('STORYBAND_')[1].split('_')[0]+'_') not in ('',)]
replace={n:'V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_'+n.split('STORYBAND_')[1] for n in ma if n.startswith('FLOOR_EDGE_NOT_GLASS_STORYBAND_') and 'V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_'+n.split('STORYBAND_')[1] in mb}
assert len(replace)==37
CAP='V24_P2_CIRCULAR_COMMONS_09_LOW_CENTRAL_ROOF_CIRCLE'
SKY='V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED'
SEAMS=sorted(n for n in mb if n.startswith('V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_'))
SMOOTH=sorted(n for n in mb if n.startswith('V64_CONSTRAINED_RELIEF_'))
assert len(SEAMS)==2 and len(SMOOTH)==4 and CAP in ma&mb and SKY in mb and SKY not in ma

# Geometry guards -- shared geometry must not unexpectedly diverge; joint face windings
# retained exactly from main instead of introducing silent cross-branch changes.
shared=ma&mb;differences=[];diff_colors=[]
for n in shared:
 ta,ka=A.graph[n];tb,kb=B.graph[n]; x=A.geometry[ka];y=B.geometry[kb]
 if not np.array_equal(ta,tb) or not np.array_equal(x.vertices,y.vertices) or not np.array_equal(x.faces,y.faces):
  differences.append(n)
 if hasattr(x.visual,"vertex_colors") and hasattr(y.visual,"vertex_colors") and not np.array_equal(x.visual.vertex_colors,y.visual.vertex_colors):diff_colors.append(n)
assert set(differences)=={CAP,'V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_01_NOT_SURVEYED','V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_02_NOT_SURVEYED'}
assert np.array_equal(A.geometry[A.graph[CAP][1]].faces,B.geometry[B.graph[CAP][1]].faces)
cap_delta=B.geometry[B.graph[CAP][1]].vertices[:,2]-A.geometry[A.graph[CAP][1]].vertices[:,2]
assert np.max(cap_delta)-np.min(cap_delta)<2.e-5 and 0.01<float(np.median(cap_delta))<0.04

# No arbitrary geometry for the unsurveyed pavilion paving seam spacing or terrain smoothing.
scene=trimesh.Scene()
# Recreate all 10 BNBU_GROUP_* nodes and their edge metadata, otherwise the
# existing main viewer loses ALL category/layer toggles even if mesh counts match.
# Do not flatten the full scene graph into a world-only geometry list.
source_edges=A.graph.to_edgelist()
parent_edge={child:(parent,record) for parent,child,record in source_edges if child!='world'}
for parent,child,record in source_edges:
 if child.startswith('BNBU_GROUP_'):
  scene.graph.update(frame_from=parent,frame_to=child,matrix=np.asarray(record['matrix']),metadata=record.get('metadata',{}))
assert len([n for n in scene.graph.nodes if n.startswith('BNBU_GROUP_')])==10
for n in A.graph.nodes_geometry:
 if n in replace or n==CAP:continue
 parent,record=parent_edge[n];k=A.graph[n][1]
 scene.add_geometry(A.geometry[k].copy(),node_name=n,geom_name=n,parent_node_name=parent,transform=np.asarray(record['matrix']),metadata=record.get('metadata',{}))
for n,ref in replace.items():
 tf,k=B.graph[ref]; new=B.geometry[k].copy()
 assert new.is_watertight and new.is_winding_consistent and new.volume>0
 # Exact inherited top area and upper/lower Z for 37 replaces; no XY movement.
 old_tf,old_k=A.graph[n];old_mesh=A.geometry[old_k];old_verts=trimesh.transform_points(old_mesh.vertices,old_tf)
 tri=old_verts[old_mesh.faces];zmax=old_verts[:,2].max();mask=(np.ptp(tri[:,:,2],axis=1)<1e-5)&(np.abs(tri[:,:,2].mean(axis=1)-zmax)<1e-4)
 oldpoly=unary_union([Polygon(t[:,:2]) for t in tri[mask] if Polygon(t[:,:2]).area>1.e-8])
 newverts=trimesh.transform_points(new.vertices,tf);newtri=newverts[new.faces];newmax=newverts[:,2].max();mm=(np.ptp(newtri[:,:,2],axis=1)<1e-5)&(np.abs(newtri[:,:,2].mean(axis=1)-newmax)<1e-4)
 newpoly=unary_union([Polygon(t[:,:2]) for t in newtri[mm] if Polygon(t[:,:2]).area>1.e-8])
 assert oldpoly.symmetric_difference(newpoly).area<0.0004,(n,oldpoly.area,newpoly.area)
 assert abs(newverts[:,2].min()-old_verts[:,2].min())<1e-4 and abs(newverts[:,2].max()-zmax)<1e-4
 parent,record=parent_edge[n]
 scene.add_geometry(new,node_name=ref,geom_name=ref,parent_node_name=parent,transform=np.asarray(record['matrix']),metadata=record.get('metadata',{}))
for n in (CAP,SKY):
 t,k=B.graph[n]
 if n==CAP:
  parent,record=parent_edge[n]
  scene.add_geometry(B.geometry[k].copy(),node_name=n,geom_name=n,parent_node_name=parent,transform=np.asarray(record['matrix']),metadata=record.get('metadata',{}))
 else:
  scene.add_geometry(B.geometry[k].copy(),node_name=n,geom_name=n,parent_node_name='BNBU_GROUP_GLASS_PROXIES_UNREGISTERED',transform=t,metadata={'surveyed':False,'metric_birdstrike_eligible':False,'confidence':'LOW_RIB_INHERITED_CURVATURE'})
assert len(scene.graph.nodes_geometry)==1380 and len([n for n in scene.graph.nodes if n.startswith("BNBU_GROUP_")])==10
main_out=MD/'BNBU_v78_RECONCILED_MAIN_EDITABLE.glb';main_out.write_bytes(scene.export('glb'))
# MAIN is a glTF Y-up scene with a -90 degree X rotation at `world`, whereas
# `trimesh.Scene.export` writes a bare root. Restore the exact main world
# rotation at the GLB JSON chunk (all Z-up raw vertex data remain identical).
# This is a coordinate-frame invariant, not an extra architectural edit.
def root_rotation(path):
 data=path.read_bytes();magic,version,total=struct.unpack_from('<4sII',data)
 assert magic==b'glTF' and version==2 and total==len(data)
 chunks=[];at=12
 while at<total:
  size,kind=struct.unpack_from('<I4s',data,at);at+=8
  chunks.append([kind,data[at:at+size]]);at+=size
 assert chunks[0][0]==b'JSON'
 doc=json.loads(chunks[0][1]);top=doc['scenes'][0]['nodes'];assert len(top)==1
 assert doc['nodes'][top[0]]['name']=='world'
 doc['nodes'][top[0]]['rotation']=[-0.7071067811865476,0.0,0.0,0.7071067811865476]
 js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
 chunks[0][1]=js
 combined=b''.join(struct.pack('<I4s',len(buf),kind)+buf for kind,buf in chunks)
 path.write_bytes(struct.pack('<4sII',b'glTF',2,len(combined)+12)+combined)
root_rotation(main_out)
side=trimesh.Scene()
for n in SEAMS:
 t,k=B.graph[n];side.add_geometry(B.geometry[k].copy(),node_name=n,geom_name=n,transform=t)
(MD/'BNBU_v78_PAVING_SEAMS_DISPLAY_ONLY.glb').write_bytes(side.export('glb'))
s=trimesh.Scene()
for n in SMOOTH:
 t,k=B.graph[n];s.add_geometry(B.geometry[k].copy(),node_name=n,geom_name=n,transform=t)
(MD/'BNBU_v78_TERRAIN_SMOOTHING_ALTERNATIVE_DISPLAY_ONLY.glb').write_bytes(s.export('glb'))
# Original / alternate GLBs kept under input: no source coordinates silently overwritten.

# GIS comes from v77, already contains inherited v75 model edits and skylight. The two
# unregistered seam entities are removed from *active* vector exports, retained only in
# the source GPKG historical layer and separate display-only GLB.
shutil.copy2(ROOT/'input/branch_v77.gpkg',D/'BNBU_v78_EDITABLE_GIS.gpkg')
with sqlite3.connect(D/'BNBU_v78_EDITABLE_GIS.gpkg') as con:
 con.execute('CREATE TABLE IF NOT EXISTS bnbu_v78_scene_membership (model_node TEXT PRIMARY KEY,scene_role TEXT NOT NULL,metric_birdstrike_eligible INTEGER NOT NULL,geometry_source TEXT,confidence TEXT)')
 statuses=[(SKY,'ACTIVE_UNSURVEYED_RIB_CONSTRAINED_GLASS',0,'branch_v77 GLB original LRC roof rim','LOW absolute position; inherited 3D curvature'),(CAP,'ACTIVE_INHERITED_CAP_Z_CONTACT_CORRECTED',0,'branch_v77 GLB','LOW absolute Z; exact inherited XY')]
 statuses += [(n,'HISTORICAL_DISPLAY_ONLY_EXCLUDED_FROM_MAIN_GLB',0,'branch_v77 GLB / v77 GIS','UNREGISTERED seam count and dimensions') for n in SEAMS]
 statuses += [(n,'ALTERNATIVE_DISPLAY_ONLY_EXCLUDED_FROM_MAIN_GLB',0,'branch_v77 GLB','UNREGISTERED smoothed terrain; main retains original v53 geometry') for n in SMOOTH]
 con.executemany('INSERT OR REPLACE INTO bnbu_v78_scene_membership VALUES (?,?,?,?,?)',statuses)
 con.commit()
source_geo=json.loads((ROOT/'input/branch_v77.geojson').read_text())
original_count=len(source_geo['features']);active=[f for f in source_geo['features'] if f['properties'].get('model_node') not in SEAMS]
assert original_count==569 and len(active)==567
source_geo['features']=active;source_geo['name']='BNBU v78 main-anchored integration; v77 unregistered roof seams excluded from active geometry'
source_geo['metadata_v78']={'parent_scene':'main v71 1379 meshes','branch_reference':'v77 1382 meshes','active_glb_nodes':1380,
  'excluded_unregistered_paving_seams':SEAMS,'terrain_smoothing_isolated':SMOOTH,'retopologized_opaque_trims':37,
  'skylight_confidence':'type and rim inherited, surface curvature unregistered; never scientific glass area',
  'horizontal':'EPSG:32649 subtract 758940, 2474080 local X,Y','vertical':'model-relative Z, no datum',
  'active_research_geometry_not_surveyed':True}
(D/'BNBU_v78_ACTIVE.geojson').write_text(json.dumps(source_geo,indent=1,ensure_ascii=False),'utf8')
root=ET.parse(ROOT/'input/branch_v77.kml'); ns={'k':'http://www.opengis.net/kml/2.2'}
for parent in root.iter():
 for elem in list(parent):
  if elem.tag.endswith('Placemark'):
   t=elem.find('k:name',ns)
   if t is not None and t.text in SEAMS:parent.remove(elem)
ET.register_namespace('','http://www.opengis.net/kml/2.2')
root.write(D/'BNBU_v78_ACTIVE.kml',encoding='utf8',xml_declaration=True)

report={'version':'v78','main_ancestor':'main v76.1 viewer / v71 1379-node GLB','branch_ancestor':'v77 1382-node GLB',
'active_meshes':1380,'main_only_retopologized_opaque_existing_trims':37,'main_original_meshes_unchanged':1379-37-1,
'cap_z_offset_model_relative':float(np.median(cap_delta)), 'skylight_inherited_geometry_added':1,
'unregistered_v77_paving_seams_excluded_active':len(SEAMS),'unregistered_v64_smooth_terrain_alternatives_isolated':len(SMOOTH),
'v71_junctions_preserved_main_original_faces':2,'old_GIS_feature_total':original_count,'active_geojson_features':len(active),
'geojson_seam_absence':all(f['properties'].get('model_node') not in SEAMS for f in active),
'main_coordinate_frame':'EPSG:32649 local x,y subtract (758940,2474080); Z relative, not surveyed','no_new_osm_ways':True,
'main_v76_photo_atlas_mesh_count_metadata_retained':1379,'forbidden_new_window_grid':0,'glass_eligible_exposure_area_m2':None,
'source_main_sha256':hashlib.sha256(MAIN.read_bytes()).hexdigest(), 'source_branch_sha256':hashlib.sha256(BRANCH.read_bytes()).hexdigest(),
'active_output_sha256':hashlib.sha256(main_out.read_bytes()).hexdigest(),
'source_main_name_to_branch_replacements':replace,'unreviewed_common_mesh_difference':[],
'known_common_mesh_differences':differences,'shared_common_count':len(shared),'main_only_count':len(ma-mb),'branch_only_count':len(mb-ma)}
(QA/'v78_geometry_compatibility.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='source_main_name_to_branch_replacements'},indent=2))