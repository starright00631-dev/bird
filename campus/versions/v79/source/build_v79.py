#!/usr/bin/env python3
"""BNBU v79: fix false top-of-dorm sampling and export real source-triangle 3D clips.

All extracted polygons/triangles come from parent v78 GLB. No new navigable
roads, entrances, bridge ends, window grids, glass exposure, terrain or roofs.
"""
from pathlib import Path
from collections import Counter
import json, math, shutil, hashlib, zipfile, sqlite3
import numpy as np
import trimesh
import fiona
ROOT=Path(__file__).resolve().parents[1]
PAR=ROOT/'parent_v78'
ZIP=ROOT/'input/BNBU_campus_geometry_v78_2026-11-12.zip'
if not (PAR/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb').exists():
 assert ZIP.exists(),'Exact v78 parent ZIP is required'
 with zipfile.ZipFile(ZIP) as zz:
  for item in zz.infolist():
   assert not item.filename.startswith('/') and '..' not in Path(item.filename).parts
  zz.extractall(ROOT/'input/_expanded')
 shutil.move(str(ROOT/'input/_expanded/BNBU_Campus_v78'),str(PAR))
S=trimesh.load(PAR/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb',force='scene',process=False)
assert len(S.graph.nodes_geometry)==1380
A=json.loads((PAR/'viewer/generated/BNBU_v74_LOCAL_3D_JUNCTION_HOTSPOTS.geojson').read_text('utf8'))
B=json.loads((PAR/'viewer/generated/BNBU_v75_BRIDGE_COMPONENT_ATLAS.json').read_text('utf8'))
C=json.loads((PAR/'viewer/generated/BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json').read_text('utf8'))
assert len(A['features'])==47 and len(B['v52_elevated_academic_bridges'])==6 and len(C['phaseII_network_disconnection_audit'])==6
D=ROOT/'data'; M=ROOT/'model'; Q=ROOT/'qa';V=ROOT/'viewer'
for p in [D,M,Q,V]: p.mkdir(exist_ok=True,parents=True)
original_glb=PAR/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb'
shutil.copy2(original_glb,M/'BNBU_v79_MAIN_INHERITED_UNMODIFIED.glb')
for name,src in [('BNBU_v79_EDITABLE_GIS.gpkg','BNBU_v78_EDITABLE_GIS.gpkg'),('BNBU_v79_ACTIVE.geojson','BNBU_v78_ACTIVE.geojson'),('BNBU_v79_ACTIVE.kml','BNBU_v78_ACTIVE.kml')]:
 shutil.copy2(PAR/'data'/src,D/name)

cache={}
def source_tris(name):
 if name not in cache:
  tf,key=S.graph[name];mesh=S.geometry[key]
  verts=trimesh.transform_points(mesh.vertices,tf)
  tris=verts[mesh.faces]
  assert np.isfinite(tris).all()
  cache[name]=tris
 return cache[name]

def sample(name,anchor):
 """All XY intersections; choose closest to EXISTING endpoint model Z, not topmost.

 Cannot infer door or navigable path even when matching a floor triangle.
 """
 tris=source_tris(name)
 xy=np.asarray(anchor[:2],dtype=float)
 a=tris[:,1,:2]-tris[:,0,:2]
 b=tris[:,2,:2]-tris[:,0,:2]
 p=xy-tris[:,0,:2]
 det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
 nonzero=np.abs(det)>1.e-10
 u=np.zeros(len(det));v=np.zeros(len(det))
 u[nonzero]=(p[nonzero,0]*b[nonzero,1]-p[nonzero,1]*b[nonzero,0])/det[nonzero]
 v[nonzero]=(a[nonzero,0]*p[nonzero,1]-a[nonzero,1]*p[nonzero,0])/det[nonzero]
 hit=nonzero&(u>=-0.002)&(v>=-0.002)&(u+v<=1.002)
 ids=np.where(hit)[0]
 assert len(ids)>0,(name,anchor)
 heights=tris[ids,0,2]+u[ids]*(tris[ids,1,2]-tris[ids,0,2])+v[ids]*(tris[ids,2,2]-tris[ids,0,2])
 # On essentially coplanar faces prefer upward normal rather than underside.
 normals=np.cross(tris[ids,1]-tris[ids,0],tris[ids,2]-tris[ids,0]);lens=np.linalg.norm(normals,axis=1)
 normals/=np.maximum(lens[:,None],1.e-10)
 priority=np.abs(heights-anchor[2])+1.e-5*(1.-np.maximum(0,normals[:,2]))
 pos=int(np.argmin(priority));i=int(ids[pos]);z=float(heights[pos]);n=normals[pos]
 top=float(np.max(heights))
 return {'node':name,'face_index':i,'model_xyz':[round(float(xy[0]),5),round(float(xy[1]),5),round(z,6)],
  'anchor_model_z':round(float(anchor[2]),6),'anchor_z_abs_error':round(abs(z-anchor[2]),6),
  'highest_intersection_z':round(top,6),'highest_intersection_bias':round(top-z,6),
  'covered':True,'xy_intersected_face_count':len(ids),
  'candidate_heights':[round(float(x),6) for x in sorted(set(np.round(heights,6)))],
  'face_normal_xyz':np.round(n,6).tolist(),'face_area_model_m2':round(float(lens[pos]/2),6),
  'vertical_layer':('low_Z_downward_facing_base_NOT_WALKABLE' if abs(z)<0.5 and n[2]<-.5 else ('ground_proxy_unverified' if abs(z)<0.5 else ('elevated_deck_unverified' if 1.0<z<15 else 'other_roof_or_unknown'))),
  'candidate_walk_upward_normal':bool(n[2]>.5),
  'route_verified':False,'door_verified':False,'absolute_z_surveyed':False}

cases=[]
def add_case(caseid,kind,name_a,name_b,point_a,point_b,provenance):
 sa=sample(name_a,point_a);sb=sample(name_b,point_b)
 ca=np.asarray(sa['model_xyz'],float);cb=np.asarray(sb['model_xyz'],float)
 gapxy=float(np.linalg.norm(ca[:2]-cb[:2]));dz=float(abs(ca[2]-cb[2]))
 cases.append({'id':caseid,'kind':kind,'a':sa,'b':sb,
   'plan_gap_model_m':round(gapxy,6),'z_gap_model_m':round(dz,6),'3d_gap_model_m':round(float(np.linalg.norm(ca-cb)),6),
   'walkability':'UNVERIFIED_NO_AUTO_CONNECTION','source':provenance,
   'geometry_evidence':'source v78 GLB literal triangle vertices',
   'vertical_datum':'model-relative, not surveyed','global_xy':'EPSG:32649 offset (-758940,-2474080)'})
for i,f in enumerate(A['features']):
 p=f['properties'];pts=p['local_points_z_up'];add_case('H%02d'%i,'inherited_47_hotspots',p['source_a'],p['source_b'],pts[0],pts[1],p['source_geometry'])
for b in B['v52_elevated_academic_bridges']:
 ends=b['endpoints'];assert len(ends)==2
 add_case('BR_'+b['id'],'v52_bridge_ends_same_deck',b['node'],b['node'],ends[0]['glb_local_xyz'],ends[1]['glb_local_xyz'],'v52_source_deck_not_entrance')
for r in C['phaseII_network_disconnection_audit']:
 d=r['dorm'];add_case('DR_'+d,'dorm_ground_to_radial','PHASEII_DORM_'+d,'PHASEII_V12_PAVING_phaseII_radial_'+d+'_surface',*r['dorm_to_radial_local_points'],'model_inherited_unsurveyed')
 add_case('RR_'+d,'radial_to_ring','PHASEII_V12_PAVING_phaseII_radial_'+d+'_surface','PHASEII_V12_PAVING_phaseII_inner_college_ring_surface',*r['radial_to_ring_local_points'],'model_inherited_unsurveyed')
assert len(cases)==65
assert all(c['a']['route_verified'] is False and c['b']['route_verified'] is False for c in cases)
DR=[c for c in cases if c['kind']=='dorm_ground_to_radial']
assert len(DR)==6 and all(abs(c['a']['model_xyz'][2])<1.e-5 and c['a']['highest_intersection_bias']>31.9 for c in DR)
assert all(abs(c['z_gap_model_m']-.044)<1.e-5 for c in DR)
# Exact face subsets: selected triangle plus adjacent same-vertical-level source triangles.
# This is an analysis-only diagnostic subset, not additional campus geometry.
scene=trimesh.Scene();clips={}
preview=[]
for case in cases:
 item={'id':case['id'],'kind':case['kind'],'plan_gap':case['plan_gap_model_m'],'z_gap':case['z_gap_model_m'],'a':{},'b':{}}
 mid=(np.asarray(case['a']['model_xyz'])+np.asarray(case['b']['model_xyz']))/2
 for end in ('a','b'):
  s=case[end];name=s['node'];tri=source_tris(name);pt=np.asarray(s['model_xyz'])
  c=tri.mean(axis=1);dist=np.linalg.norm(c[:,:2]-pt[:2],axis=1)
  # Keep local source facets near chosen height, suppress roof/other levels.
  sel=(dist<5.5)&(np.abs(c[:,2]-pt[2])<.45)
  sel[s['face_index']]=True
  idx=np.where(sel)[0]
  if len(idx)>120:
   idx=idx[np.argsort(dist[idx])[:120]]
   if s['face_index'] not in idx:idx[-1]=s['face_index']
  chosen=tri[idx].astype('float64')
  assert np.all(np.isfinite(chosen))
  verts=chosen.reshape(-1,3)
  mesh=trimesh.Trimesh(vertices=verts,faces=np.arange(len(verts)).reshape(-1,3),process=False)
  # Use distinct diagnostic opaque colors; the source triangles are exact.
  mesh.visual.face_colors=np.tile(np.array([45,163,210,230] if end=='a' else [241,147,53,230],dtype='uint8'),(len(mesh.faces),1))
  node='V79_DIAGNOSTIC_'+case['id']+'_'+end
  scene.add_geometry(mesh,node_name=node,geom_name=node)
  clips[node]={'parent_mesh':name,'source_face_ids':[int(x) for x in idx],
               'num_faces':len(idx),'selected_source_triangle':s['face_index']}
  # Render data stays centered: vertices are exact source coordinates BEFORE local subtraction.
  item[end]={'source_mesh':name,'faces':np.round(chosen-mid,4).tolist(),
             'anchor':np.round(pt-mid,4).tolist(),'z':s['model_xyz'][2],
             'normal':s['face_normal_xyz'],'candidate_heights':s['candidate_heights']}
 item['world_mid']=np.round(mid,5).tolist()
 preview.append(item)
mesh_out=M/'BNBU_v79_REAL_SOURCE_FACE_CLIPS_ONLY.glb';mesh_out.write_bytes(scene.export('glb'))
# Roundtrip: imported vertex source coordinates must match original selected model triangles.
rt=trimesh.load(mesh_out,force='scene',process=False)
assert len(rt.graph.nodes_geometry)==130
maxerr=0.
for node,record in clips.items():
 tf,k=rt.graph[node];got=trimesh.transform_points(rt.geometry[k].vertices,tf)
 orig=source_tris(record['parent_mesh'])[record['source_face_ids']].reshape(-1,3)
 assert len(got)==len(orig)
 err=float(np.max(np.abs(got-orig)));maxerr=max(maxerr,err)
 assert err<0.0002,(node,err)
(Q/'v79_face_clip_provenance.json').write_text(json.dumps(clips,indent=1),'utf8')
(V/'v79_canvas_geometry_data.json').write_text(json.dumps(preview,separators=(',',':')),'utf8')
# Preserve ALL inherited 143 spatial layers and 567 active features; attach nonspatial QA.
with sqlite3.connect(D/'BNBU_v79_EDITABLE_GIS.gpkg') as con:
 con.execute('CREATE TABLE IF NOT EXISTS bnbu_v79_surface_layer_checks (case_id TEXT,end_letter TEXT,source_node TEXT,selected_face INTEGER,model_x REAL,model_y REAL,model_z REAL,highest_face_z REAL,layer_bias REAL,source_normal_z REAL,route_verified INTEGER,surveyed INTEGER,PRIMARY KEY(case_id,end_letter))')
 for c in cases:
  for end in ('a','b'):
   s=c[end];con.execute('INSERT OR REPLACE INTO bnbu_v79_surface_layer_checks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
      (c['id'],end,s['node'],s['face_index'],*s['model_xyz'],s['highest_intersection_z'],s['highest_intersection_bias'],s['face_normal_xyz'][2],0,0))
 con.commit()
with sqlite3.connect(D/'BNBU_v79_EDITABLE_GIS.gpkg') as con:
 assert con.execute("SELECT COUNT(*) FROM gpkg_contents WHERE data_type='features'").fetchone()[0]==143
assert len(json.loads((D/'BNBU_v79_ACTIVE.geojson').read_text())['features'])==567
# Verify actual vertical facade base edges, not just a downward-facing floor footprint.
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,nearest_points
facade_checks=[]
for c in DR:
 dorm=c['id'].replace('DR_','');source='PHASEII_DORM_'+dorm
 tri=source_tris(source);cr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);lens=np.linalg.norm(cr,axis=1)
 normals=cr/np.maximum(lens[:,None],1e-12)
 wall_edges=[]
 for j,(t,n) in enumerate(zip(tri,normals)):
  if abs(float(n[2]))>.2 or float(t[:,2].min())>.001: continue
  low=t[np.abs(t[:,2])<.001]
  if len(low)>=2 and np.linalg.norm(low[0,:2]-low[1,:2])>1.e-6:
   wall_edges.append((j,LineString(low[:2,:2])))
 assert len(wall_edges)>=50
 road=Point(c['b']['model_xyz'][:2]);nearest=min(wall_edges,key=lambda x:x[1].distance(road))
 wallpoint=nearest_points(nearest[1],road)[0]
 model_gap=float(road.distance(wallpoint))
 assert abs(model_gap-c['plan_gap_model_m'])<.001,(dorm,model_gap,c['plan_gap_model_m'])
 assert np.linalg.norm(np.array([wallpoint.x,wallpoint.y])-np.array(c['a']['model_xyz'][:2]))<.001
 facade_checks.append({'dorm':dorm,'road_to_existing_vertical_facade_base_model_m':round(model_gap,6),
   'facade_base_xy_local':[round(wallpoint.x,6),round(wallpoint.y,6)],
   'vertical_sidewall_source_node':source,'vertical_sidewall_source_triangle':nearest[0],
   'wall_face_normal_xyz':np.round(normals[nearest[0]],6).tolist(),
   'candidate_entrance_verified':False,'public_walkable_connection_verified':False,
   'note':'Closest model facade-base edge is not a mapped door. Z=0 floor face points down.'})
(Q/'v79_dorm_facade_ground_edges.json').write_text(json.dumps(facade_checks,indent=2),'utf8')
stat={'version':'v79','parent_v78_sha256':hashlib.sha256(original_glb.read_bytes()).hexdigest(),
 'active_main_glb_sha256':hashlib.sha256((M/'BNBU_v79_MAIN_INHERITED_UNMODIFIED.glb').read_bytes()).hexdigest(),
 'main_meshes_unchanged':1380,'accepted_new_campus_geometries':0,'display_only_real_source_face_clip_meshes':len(rt.graph.nodes_geometry),
 'source_clip_max_vertex_difference_model_m':maxerr,'47_hotspots':47,'bridge_source_endpoints':12,
 'dorm_radial_and_radial_ring_pairs':12,'endpoints_layer_rechecked':130,
 'false_roof_z_32m_bias_detected_for_dorms':6,
 'dorm_ground_anchor_faces_are_downward_facing_undersides_NOT_ENTRANCES':6,
 'vertical_facade_base_edges_independently_matched_to_road_gap':len(facade_checks),
 'dorm_floor_z_selected':[c['a']['model_xyz'][2] for c in DR],
 'dorm_road_z_selected':[c['b']['model_xyz'][2] for c in DR],
 'dorm_gaps_plan_m':[c['plan_gap_model_m'] for c in DR],
 'dorm_gaps_3d_corrected_model_m':[c['3d_gap_model_m'] for c in DR],
 'dorm_rooftop_3d_gap_not_usable_as_ground_access':True,'new_osm_ways':0,'new_roads_bridges_glazing':0,
 'GPKG_spatial_layers_preserved':143,'active_geojson_features_preserved':567,
 'source_handdrawn':'https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg',
 'site_status':'unsurveyed; not a route graph or measured birdstrike exposure'}
(Q/'v79_build_validation.json').write_text(json.dumps(stat,indent=2),'utf8')
(Q/'v79_layer_aware_junctions.json').write_text(json.dumps({'summary':stat,'cases':cases},indent=2),'utf8')
print(json.dumps({k:v for k,v in stat.items() if k not in ('dorm_gaps_plan_m','dorm_gaps_3d_corrected_model_m')},indent=2))