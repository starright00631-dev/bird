#!/usr/bin/env python3
"""BNBU v85: extend exact V52 source triangle inspector to both V60 shore ends.

No guessed roads, landings, or fabricated triangles are added to the scientific GLB.
Source parent is the verified v84 GLB; scene local coordinates are model-relative.
For V60 endpoints select extreme east/west *upward* source face centroids.
Distances are computed to actual source triangles, not XY proximity.
"""
from pathlib import Path
import hashlib, json, re
import numpy as np
import trimesh

R=Path(__file__).resolve().parents[1]
PARENT=R/'model/BNBU_v84_FULL_EDITABLE.glb'
OLD_INSPECTOR=R/'viewer/BNBU_v84_V52_Actual_Triangle_3D_Inspector.html'
OLD_PROBE=R/'qa/v83_v52_probe.json'
V60='V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE'
TARGET=R/'viewer/BNBU_v85_V52_V60_Actual_SourceTriangle_3D_Inspector.html'
JSON_OUT=R/'qa/v85_v60_endpoints_3d.json'
SCENE=trimesh.load(PARENT,force='scene',process=False)
assert len(SCENE.graph.nodes_geometry)==1346
assert sum(len(g.faces) for g in SCENE.geometry.values())==691593

def mesh_for(node):
    tf,key=SCENE.graph[node];g=SCENE.geometry[key].copy();g.apply_transform(tf)
    return g

def rounded(a,n=7):return np.asarray(a).round(n).tolist()

bridge_probes=json.loads(OLD_PROBE.read_text('utf-8'))
assert len(bridge_probes)==12 and len({p['id'] for p in bridge_probes})==12
# Confirm every inherited V52 source triangle and face-normal is still present.
for probe in bridge_probes:
    m=mesh_for(probe['bridge_node']); f=probe['source_face_index']
    assert np.allclose(m.triangles[f],probe['source_triangle_xyz'],rtol=0,atol=8e-7),probe['id']
    assert np.allclose(m.face_normals[f],probe['source_face_normal_xyz'],rtol=0,atol=8e-7),probe['id']
    assert not probe['is_routable']

m=mesh_for(V60)
assert len(m.faces)==796
face_top=np.flatnonzero(m.face_normals[:,2]>.95)
assert len(face_top)==198
# Representative interior points close to each mesh extremity. These are not
# inferred site entrances, and the chosen centroids need not be the real landing.
end_ids={'W':int(face_top[np.argmin(m.triangles_center[face_top,0])]),
         'E':int(face_top[np.argmax(m.triangles_center[face_top,0])])}

# Candidate surfaces are the *existing* walk, terrain bank, lakeside slabs or lake,
# not arbitrary buildings at a similar XY position. Overlay V42 duplicate side
# skins are excluded to keep independent source candidates separated.
classes=('SHORE_','WALK_','V61_','V71_','ROAD_','LAKE_','V50_LAKE_')

v60probes=[]
nearest_meshes=set()
for side,face_id in end_ids.items():
    xyz=np.asarray(m.triangles_center[face_id],dtype=float)
    candidates=[]
    for node in SCENE.graph.nodes_geometry:
        if node==V60 or not node.startswith(classes):continue
        target=mesh_for(node)
        bound=target.bounds
        lower=np.maximum(np.maximum(bound[0]-xyz,xyz-bound[1]),0.)
        if np.linalg.norm(lower)>25:continue
        near,ds,idx=trimesh.proximity.closest_point_naive(target,xyz[None,:])
        dis=float(ds[0])
        if dis>=25:continue
        fi=int(idx[0]);candidates.append({
            'node':node,'distance_3d_model_m':round(dis,8),
            'distance_xy_model_m':round(float(np.linalg.norm(near[0,:2]-xyz[:2])),8),
            'source_face_index':fi,'nearest_point_xyz_model':rounded(near[0]),
            'delta_z_model_m':round(float(near[0,2]-xyz[2]),8),
            'face_normal':rounded(target.face_normals[fi]),
            'triangle_xyz':rounded(target.triangles[fi]),
            'surface_type':('water' if node.startswith(('LAKE_','V50_LAKE_')) else
                            'shore' if node.startswith('SHORE_') else
                            'unsurveyed_landing_proxy' if node.startswith(('V61_','V71_')) else
                            'walk_or_road_model')
        })
    # Do not substitute a lake surface for a public pedestrian landing.
    land=sorted((x for x in candidates if x['surface_type']!='water'),key=lambda x:x['distance_3d_model_m'])
    water=sorted((x for x in candidates if x['surface_type']=='water'),key=lambda x:x['distance_3d_model_m'])
    assert land and water if side=='E' else land
    probe={'id':'V60_'+side,'bridge_node':V60,'end':side,
           'endpoint_definition':'centroid of extreme '+('west' if side=='W' else 'east')+' upward-facing deck source triangle; NOT surveyed landing',
           'xyz_local_model':rounded(xyz,10), 'model_z':float(xyz[2]),
           'source_face_index':face_id,'source_triangle_xyz':rounded(m.triangles[face_id]),
           'source_face_normal_xyz':rounded(m.face_normals[face_id]),
           'parent_mesh_triangle_count':len(m.faces),
           'candidate_model_neighbors':land[:7],
           'water_model_neighbors':water[:3],
           'nearest_land_3d_model_m':land[0]['distance_3d_model_m'],
           'nearest_land_node':land[0]['node'],
           'is_verified_connected':False,'is_routable':False,'status':'UNVERIFIED_MODEL_GEOMETRY_ONLY',
           'confidence':'EXACT_INHERITED_TRIANGLE_BUT_UNSURVEYED_WORLD_COORDINATES',
           'surface_qualifier':'V60 deck photo supports type; neither end confirms an accessible landing',
           'note':'All distances and z-values are relative to one unsurveyed scene; do not create bridge, ramp, or road from XY proximity.'}
    v60probes.append(probe)
    nearest_meshes.update(x['node'] for x in land[:4]+water[:2])

# Source-geometry parity, including 12 inherited bridgehead source faces.
for p in bridge_probes:
    assert p['bridge_node'] in SCENE.graph.nodes_geometry
all_probes=bridge_probes+v60probes

def plot_triangles(mesh,node,kind):
    arr=[]
    for i,t in enumerate(mesh.triangles):
        arr.append([node,i,kind,*rounded(t.reshape(-1),4)])
    return arr

old=OLD_INSPECTOR.read_text('utf-8')
rx=r'(const DATA=)(.*?)(;const c=)'
match=re.search(rx,old,re.S)
assert match
body=json.loads(match.group(2));assert len(body['probes'])==12
body['parent']='v84 SHA256 '+hashlib.sha256(PARENT.read_bytes()).hexdigest()
body['title']='14 source-face bridge/shore ends: v52 + v60'
# retain all original bridge preview geometry: never regenerate V52 triangles
body['probes']=all_probes
body['tris'].extend(plot_triangles(m,V60,'bridge'))
# Show exact selected neighboring source faces, and a handful of neighboring
# top triangles for context. They are all indexed original source mesh faces.
for node in sorted(nearest_meshes):
    g=mesh_for(node)
    near_faces=set()
    for probe in v60probes:
        for ca in (probe['candidate_model_neighbors']+probe['water_model_neighbors']):
            if ca['node']==node:
                f=int(ca['source_face_index']);near_faces.add(f)
                # Include only bounded local surface context, not entire 40k-face shore.
                centers=g.triangles_center
                dist=np.linalg.norm(centers[:,:2]-centers[f,:2],axis=1)
                top=np.flatnonzero((dist<=3.0)&(g.face_normals[:,2]>.75))
                near_faces.update(int(z) for z in top[:75])
    for f in sorted(near_faces):body['tris'].append([node,int(f),'neighbor',*rounded(g.triangles[f].reshape(-1),4)])
assert all(p['is_routable'] is False for p in body['probes'])

web=old[:match.start(2)]+json.dumps(body,ensure_ascii=False,separators=(',',':'))+old[match.end(2):]
web=web.replace('BNBU v83 · V52 12桥端真实源三角面','BNBU v85 · V52十二桥端 + V60东西岸真实源三角面')
web=web.replace('BNBU v83 · V52 12桥端三角面定位','BNBU v85 · V52 / V60 十四个源三角面端点')
web=web.replace('全部六座桥','六桥与V60全部端点').replace('12 个端点标记','14 个端点标记')
web=web.replace('const BRIDGE_NAMES=[...new Set(DATA.probes.map(x=>x.bridge_node))];','const BRIDGE_NAMES=[...new Set(DATA.probes.map(x=>x.bridge_node))];')
web=web.replace("x.bridge_node.split('CONNECTION_')[1].slice(0,2)","(x.bridge_node.includes('CONNECTION_')?x.bridge_node.split('CONNECTION_')[1].slice(0,2):'V60')")
web=web.replace("DATA.probes[i].bridge_node.split('CONNECTION_')[1].slice(0,2)","(DATA.probes[i].bridge_node.includes('CONNECTION_')?DATA.probes[i].bridge_node.split('CONNECTION_')[1].slice(0,2):'V60')")
web=web.replace('(selected+1)%12','(selected+1)%DATA.probes.length')
web=web.replace('main GLB保持1347网格不变','v84 主 GLB 1346 网格保持不变')
web=web.replace('12个桥端均未证实可通行','14个端点均未证实可通行')
web=web.replace("sourceProbes:12","sourceProbes:14").replace("version:'v83'","version:'v85'")
web=web.replace('window.__BNBU_V83__','window.__BNBU_V85__')
web=web.replace("(r.model_z>3?'Level 2 proxy':'Uncertain')","(r.id.startsWith('V60')?'East-lake deck model-relative':r.model_z>3?'Level 2 proxy':'Uncertain')")
web=web.replace('最近向上表面：','最近非水面源三角面：')
web=web.replace("'\\n\\n结论：不具备测绘和现场入口证据；无法确认可通行。'","'\\n\\n结论：现有三角网格不可单独证明现场可通行；东端可能终止于水面上方，严禁从模型平面接近自动补路。'")
# The old inspector note represented the v52 0.04-0.15 gaps only; avoid falsely
# applying that range to V60, where east shore is >17 model meters away.
web=web.replace('该 0.04–0.15 模型米间距来自同一个未测绘的 GLB','所有局部间距来自同一个未测绘的 GLB，V60 东岸最近地表距离另见面板')
web=web.replace("byId('all').onclick=()=>{all=true;center=[75,-40,4];zoom=1.5;draw()}","byId('all').onclick=()=>{all=true;center=[165,-52,3];zoom=1.05;draw()}")
TARGET.write_text(web,'utf-8')
# Independent detailed report records native precision (not 4-decimal preview).
report={'version':'v85','parent':'v84','parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),
        'parent_source_nodes':1346,'parent_source_triangles':691593,
        'v52_source_faces_checked_unchanged':len(bridge_probes),'v60_source_faces':len(m.faces),
        'v60_mesh_transform':rounded(SCENE.graph[V60][0]),
        'v60_ends':v60probes, 'total_endpoint_probes':len(all_probes),
        'new_scientific_geometry_count':0,
        'change_class':'read-only exact source-surface inspection, interactively inspectable independent downstream geometry validation',
        'coordinate_frame':'model XY relative UTM EPSG32649 offset (758940,2474080); unsurveyed Z relative; GIS EPSG4326',
        'birdstrike_glass_area_eligible':False,'routable_endpoints_certified':0,
        'inspector_faces_rendered_from_original_source':len(body['tris']),
        'viewer_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        'verified_never_add_roads_due_to_xy_proximity':True,
        'no_guessed_glazing_rails_roof_or_route_added':True}
JSON_OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'v60_ends':[(p['id'],p['source_face_index'],p['nearest_land_3d_model_m'],p['nearest_land_node']) for p in v60probes], 'triangles':len(body['tris']),'new_inspector':str(TARGET)},ensure_ascii=False))