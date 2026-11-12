#!/usr/bin/env python3
"""Recheck inherited connector candidates against actual active GLB triangles.
A source triangle under a projected point does NOT establish a navigable doorway.
No geometry is created from these diagnostics.
"""
from pathlib import Path
import json,math,collections
import numpy as np,trimesh
R=Path(__file__).resolve().parent
P=R/'viewer/generated'
S=trimesh.load(R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb',force='scene',process=False)
_cache={}
def sample(node,xy):
 if node not in S.graph.nodes_geometry:return {'covered':False,'why':'node_not_in_active_glb','node':node}
 if node not in _cache:
  transform,k=S.graph[node];mesh=S.geometry[k];v=trimesh.transform_points(mesh.vertices,transform)
  tri=v[mesh.faces];xytri=tri[:,:,:2];e1=xytri[:,1]-xytri[:,0];e2=xytri[:,2]-xytri[:,0]
  denom=e1[:,0]*e2[:,1]-e2[:,0]*e1[:,1]
  _cache[node]=(tri,e1,e2,denom)
 tri,e1,e2,denom=_cache[node];p=np.asarray(xy,float)-tri[:,0,:2]
 ok=np.abs(denom)>1e-10
 u=np.full(len(tri),np.nan);v=np.full(len(tri),np.nan)
 u[ok]=(p[ok,0]*e2[ok,1]-p[ok,1]*e2[ok,0])/denom[ok]
 v[ok]=(e1[ok,0]*p[ok,1]-e1[ok,1]*p[ok,0])/denom[ok]
 inside=ok&(u>=-0.002)&(v>=-0.002)&(u+v<=1.002)
 ids=np.where(inside)[0]
 if len(ids)==0:
  # Do not infer a connection, Z or surface normal when no triangle covers XY.
  return {'covered':False,'why':'no_source_triangle_below_point','node':node}
 heights=tri[ids,0,2]+u[ids]*(tri[ids,1,2]-tri[ids,0,2])+v[ids]*(tri[ids,2,2]-tri[ids,0,2])
 j=int(np.argmax(heights));i=int(ids[j]);z=float(heights[j]);norm=np.cross(tri[i,1]-tri[i,0],tri[i,2]-tri[i,0]);q=np.linalg.norm(norm)
 n=(norm/q).tolist() if q>0 else None
 return {'covered':True,'node':node,'surface_z_model_relative':round(z,6),'face_index':i,'normal_xyz':[round(x,5) for x in n] if n else None,'normal_z_abs':round(abs(n[2]),5) if n else None,'source_triangle_area':round(q/2,5),'multiple_triangles_xy':int(len(ids))}
def pair(node1,node2,coords):
 if len(coords)<2:return {'source_a':node1,'source_b':node2,'evidence_insufficient':True}
 a,b=coords[0],coords[1];sa=sample(node1,a[:2]);sb=sample(node2,b[:2]);xy=float(np.linalg.norm(np.asarray(a[:2])-np.asarray(b[:2])))
 out={'source_a':node1,'source_b':node2,'model_plan_endpoint_gap_m':round(xy,4),'a':sa,'b':sb,'navigable_verified':False,'photo_registered':False}
 if sa['covered'] and sb['covered']:
  dz=sa['surface_z_model_relative']-sb['surface_z_model_relative'];out['local_surface_z_delta_m']=round(dz,5)
  out['local_actual_surface_3d_gap_m']=round(math.hypot(xy,dz),5)
  out['both_face_normals_z_abs']=[sa.get('normal_z_abs'),sb.get('normal_z_abs')]
 else:out['local_actual_surface_3d_gap_m']=None
 return out
hot=json.loads((P/'BNBU_v74_LOCAL_3D_JUNCTION_HOTSPOTS.geojson').read_text())
assert len(hot['features'])==47
records=[]
for feat in hot['features']:
 p=feat['properties'];rec=pair(p['source_a'],p['source_b'],p['local_points_z_up']);rec['original_category']=p['source_type'];rec['original_provenance']=p['source_geometry'];rec['original_navigation_connection_proven']=p['navigation_connection_proven'];records.append(rec)
bridge=json.loads((P/'BNBU_v75_BRIDGE_COMPONENT_ATLAS.json').read_text())
ends=[]
for b in bridge['v52_elevated_academic_bridges']:
 for e in b['endpoints']:
  sampled=sample(b['node'],e['glb_local_xyz'][:2]);ends.append({'bridge_id':b['id'],'end':e['end'],'node':b['node'],'model_xyz':e['glb_local_xyz'],'candidate_building':e['linked_building_candidate'],'source_face':sampled,'door_threshold_verified':False,'photo_registration':False})
assert len(ends)==12
arch=json.loads((P/'BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json').read_text());phase=arch['phaseII_network_disconnection_audit'];assert len(phase)==6
ph=[]
for row in phase:
 dorm=row['dorm'];rad='PHASEII_V12_PAVING_phaseII_radial_'+dorm+'_surface';ring='PHASEII_V12_PAVING_phaseII_inner_college_ring_surface';db='PHASEII_DORM_'+dorm
 p1=pair(db,rad,row['dorm_to_radial_local_points']);p2=pair(rad,ring,row['radial_to_ring_local_points'])
 ph.append({'dorm':dorm,'dorm_to_radial':p1,'radial_to_ring':p2,'route_or_portal_verified':False,'do_not_create_road':True})
summary={'version':'v78','main_mesh_count':len(S.graph.nodes_geometry),'original_47_hotspots_rechecked':len(records),'hotspot_both_xy_project_to_current_mesh':sum(x['a']['covered'] and x['b']['covered'] for x in records),'hotspot_missing_source_triangle':sum(not x['a']['covered'] or not x['b']['covered'] for x in records),'V52_bridge_endpoint_count':len(ends),'V52_endpoint_has_source_triangle':sum(x['source_face']['covered'] for x in ends),'PhaseII_dorm_to_radial_candidates':len(ph),'PhaseII_radial_to_ring_candidates':len(ph),'route_links_added':0,'assumed_glass_area_added':0,'horizontal_crs':'EPSG:32649 minus (758940,2474080)','vertical':'relative model Z, NOT surveying','important':'Source triangles and normals are local model diagnostics, not proof of pedestrian accessibility, photo registration or door geometry.'}
out={'summary':summary,'hotspot_pairs':records,'bridge_12_ends':ends,'phaseII_12_gap_types':ph}
(R/'qa/v78_junction_triangle_recheck.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))