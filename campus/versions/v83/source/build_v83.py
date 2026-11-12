#!/usr/bin/env python3
"""BNBU v83: source-triangle, normal-aware bridge-end spatial QA; never synthesize a route.

Parent v82 is preserved byte-for-byte (main geometry and all physical GIS). We generate
12 endpoint probes and source-face clips as QA-only evidence; not main geometric features.
"""
from pathlib import Path
import os, json, hashlib, shutil, math
import numpy as np, trimesh, fiona
from scipy.spatial import cKDTree
from pyproj import Transformer
from fiona.crs import CRS
from shapely.geometry import mapping,Point
R=Path(__file__).resolve().parents[1];I=R/'input';O=R/'model';D=R/'data';Q=R/'qa'
for folder in (O,D,Q):folder.mkdir(exist_ok=True)
for suffix in ('FULL_EDITABLE.glb','ACTIVE.geojson','ACTIVE.kml','DISPLAY_ONLY.geojson','DISPLAY_ONLY.kml','EDITABLE_GIS.gpkg'):
 src=I/('BNBU_v82_'+suffix);dst=(O if suffix.endswith('.glb') else D)/('BNBU_v83_'+suffix)
 shutil.copy2(src,dst)
 assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dst.read_bytes()).digest()
s=trimesh.load(I/'BNBU_v82_FULL_EDITABLE.glb',force='scene',process=False)
assert len(s.graph.nodes_geometry)==1347
bridges=sorted(n for n in s.graph.nodes_geometry if n.startswith('V52_LEVEL2_PEDESTRIAN_CONNECTION_'))
assert len(bridges)==6
# This is model-local EPSG:32649 minus stated offsets, NOT measured Z.
geo=Transformer.from_crs(32649,4326,always_xy=True)
clip=trimesh.Scene(); records=[]
# Stable pure geometry content: parent vertices, faces and world transforms untouched.
for name in bridges:
 mat,key=s.graph[name];m=s.geometry[key]
 clip.add_geometry(m.copy(),node_name=name,geom_name=name,transform=mat)
 verts=trimesh.transform_points(m.vertices,mat)
 tris=verts[m.faces]
 norms=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);sizes=np.linalg.norm(norms,axis=1)
 norm=np.divide(norms,sizes[:,None],out=np.zeros_like(norms),where=sizes[:,None]>1e-8)
 upper=np.flatnonzero(norm[:,2]>.7)
 assert len(upper)>0
 tv=tris[upper].reshape(-1,3)
 unique=np.unique(tv.round(5),axis=0)
 xy=unique[:,:2]
 cov=np.cov(xy.T); eigvals,eigvecs=np.linalg.eigh(cov);axis=eigvecs[:,np.argmax(eigvals)];proj=xy@axis
 # terminal cross-sections: real upper mesh vertices in endmost 4% projected range
 for side,sign in (('A',-1),('B',1)):
  lo,hi=proj.min(),proj.max();tol=max((hi-lo)*.04,.22)
  extremals=unique[proj<=lo+tol] if sign<0 else unique[proj>=hi-tol]
  pt=extremals.mean(axis=0)
  # nearest actual UP-facing source triangle (triangle ID is parent m.faces index)
  i=int(upper[np.argmin(np.linalg.norm(tris[upper].mean(axis=1)[:,:2]-pt[:2],axis=1))])
  face=tris[i];normal=norm[i];pt[2]=face[:,2].mean()
  # Snap the terminal mean to the exact ORIGINAL upper triangle (3D closest point).
  pt=trimesh.triangles.closest_point(face[None],pt[None])[0]
  assert normal[2]>.7
  lon,lat=geo.transform(float(pt[0]+758940),float(pt[1]+2474080))
  rec={'id':f"{name.split('_CONNECTION_')[1][:2]}_{side}",'bridge_node':name,'end':side,
    'xyz_local_model':[float(x) for x in pt],'approx_lonlat_from_inherited_crs':[lon,lat],
    'source_face_index':i,'source_triangle_xyz':face.round(7).tolist(),
    'source_face_normal_xyz':normal.round(7).tolist(),
    'parent_mesh_triangle_count':len(m.faces),'model_z':float(pt[2]),
    'candidate_model_neighbors':[],'is_verified_connected':False,'is_routable':False,
    'status':'UNVERIFIED_MODEL_GEOMETRY_ONLY','official_map':'https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg'}
  records.append(rec)
assert len(records)==12
# Position and normal filtering rather than XY-only nearest neighbor. Every candidate
# is an existing triangle; even zero model-gap does not certify a traversable bridge.
for rec in records:
 p=np.asarray(rec['xyz_local_model']);results=[]
 for name in s.graph.nodes_geometry:
  if name in bridges:continue
  tf,k=s.graph[name];m=s.geometry[k];b=trimesh.transform_points(m.bounds,tf)
  if (p[0]<b[:,0].min()-12 or p[0]>b[:,0].max()+12 or p[1]<b[:,1].min()-12 or p[1]>b[:,1].max()+12 or p[2]<b[:,2].min()-2 or p[2]>b[:,2].max()+2):continue
  v=trimesh.transform_points(m.vertices,tf);t=v[m.faces]
  c=t.mean(axis=1)
  subset=np.flatnonzero((np.abs(c[:,0]-p[0])<13)&(np.abs(c[:,1]-p[1])<13)&(np.abs(c[:,2]-p[2])<2))
  if len(subset)==0:continue
  tt=t[subset]
  norm=np.cross(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]);norm=np.divide(norm,np.linalg.norm(norm,axis=1)[:,None],out=np.zeros_like(norm),where=np.linalg.norm(norm,axis=1)[:,None]>1e-8)
  sub=subset[norm[:,2]>.65];tt=t[sub];norm=norm[norm[:,2]>.65]
  if not len(sub):continue
  cp=trimesh.triangles.closest_point(tt,np.broadcast_to(p, (len(sub),3)))
  dist=np.linalg.norm(cp-p,axis=1);j=int(np.argmin(dist))
  if dist[j]<12:
   results.append({'node':name,'distance_3d_model_m':round(float(dist[j]),5),
       'source_face_index':int(sub[j]),'nearest_point_xyz_model':cp[j].round(6).tolist(),
       'delta_z_model_m':round(float(cp[j,2]-p[2]),5),
       'face_normal':norm[j].round(6).tolist(),
       'triangle_xyz':tt[j].round(7).tolist()})
 results.sort(key=lambda x:x['distance_3d_model_m'])
 # Keep distinct candidates; nearby canopies/roofs can be ABOVE rather than walkable.
 rec['candidate_model_neighbors']=results[:6]
 rec['closest_model_3d_distance_m']=results[0]['distance_3d_model_m'] if results else None
 rec['closest_model_3d_neighbor']=results[0]['node'] if results else None
 rec['note']='Nearest *upward-facing* model triangle is not a door, surveyed landing, or confirmed public pedestrian route.'
# Export only the EXISTING source faces used in QA, never synthetic connectors.
# To avoid boundary stitching, each face is a deliberately open source triangle.
triangles=trimesh.Scene();unique=set()
for r in records:
 for e in [ {'node':r['bridge_node'],'source_face_index':r['source_face_index']}, *r['candidate_model_neighbors'][:1] ]:
  key=(e['node'],e['source_face_index'])
  if key in unique:continue
  unique.add(key);tf,geom=s.graph[e['node']];m=s.geometry[geom]
  sub=trimesh.Trimesh(vertices=m.vertices.copy(),faces=m.faces[[e['source_face_index']]].copy(),process=False)
  triangles.add_geometry(sub,node_name=f'SOURCE_FACE_{len(unique):02d}_{e["node"][:40]}',geom_name=f'SOURCE_FACE_{len(unique):02d}',transform=tf)
(O/'BNBU_v83_V52_SOURCE_FACE_CLIPS_ONLY.glb').write_bytes(triangles.export('glb'))
# Separate QA GPKG: physical GIS 146 layers remains unchanged, avoiding a fake routable layer.
qa_gpkg=Q/'BNBU_v83_V52_BRIDGE_ENDPOINT_DIAGNOSTIC.gpkg'
if qa_gpkg.exists():qa_gpkg.unlink()
schema={'geometry':'Point','properties':{'probe_id':'str','source_node':'str','face_id':'int','z_relative':'float','normal_z':'float','nearest_3d':'float','closest_node':'str','verified':'int','surveyed':'int','routable':'int','evidence':'str'}}
with fiona.open(qa_gpkg,'w',driver='GPKG',layer='qa_v52_12_bridge_ends_not_routable',crs=CRS.from_epsg(4326),schema=schema) as ds:
 for r in records:
  a,b=r['approx_lonlat_from_inherited_crs'];ds.write({'geometry':mapping(Point(a,b)),'properties':{
   'probe_id':r['id'],'source_node':r['bridge_node'],'face_id':r['source_face_index'],
   'z_relative':r['model_z'],'normal_z':r['source_face_normal_xyz'][2],
   'nearest_3d':r['closest_model_3d_distance_m'] or -1.,'closest_node':r['closest_model_3d_neighbor'] or 'NONE',
   'verified':0,'surveyed':0,'routable':0,'evidence':'V82 source triangles only; not field-verified'}})
(Q/'v83_v52_probe.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf8')
report={'parent':'v82','version':'v83','main_model_changed_nodes':0,'main_glb_nodes':len(s.graph.nodes_geometry),
 'main_faces_unchanged':sum(len(s.geometry[s.graph[n][1]].faces) for n in s.graph.nodes_geometry),
 'physical_GIS_unchanged':True,'V52_bridge_source_meshes':len(bridges),
 'bridge_endpoint_probes':len(records),'separate_original_face_clip_meshes':len(unique),
 'candidate_source_triangles_per_endpoint':[len(r['candidate_model_neighbors']) for r in records],
 'all_routability_unverified':True,'no_new_windows_roads_bridges_terrain':True,
 'main_glb_sha256':hashlib.sha256((O/'BNBU_v83_FULL_EDITABLE.glb').read_bytes()).hexdigest(),
 'source':'parent v82 actual original GLB only','coordinates':'EPSG:32649 local minus (758940,2474080), Z model-relative'}
(Q/'v83_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))