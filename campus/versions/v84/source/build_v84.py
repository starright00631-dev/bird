#!/usr/bin/env python3
"""v84: eliminate ONLY a proven geometrically coincident, same-colour V42 road side overlay.
No fabricated or changed campus coordinates. Original mesh is retained in separate GLB.
Direct parent is v83, not the archived v10 checkpoint.
"""
from pathlib import Path
import trimesh, numpy as np, json, shutil, hashlib

R=Path(__file__).resolve().parents[1]; I=R/'input'; O=R/'model'; D=R/'data'; Q=R/'qa'
for d in (O,D,Q):d.mkdir(parents=True,exist_ok=True)
P=I/'BNBU_v83_FULL_EDITABLE.glb'
s=trimesh.load(P,force='scene',process=False)
BASE='ROAD_000'; DUP='V42_FACET_SIDE_ROAD_000'
assert len(s.graph.nodes_geometry)==1347
parent=s.geometry[s.graph[BASE][1]]
redundant=s.geometry[s.graph[DUP][1]]
assert len(parent.faces)==416 and len(redundant.faces)==314
assert np.array_equal(s.graph[BASE][0],s.graph[DUP][0])
assert np.max(np.abs(parent.bounds-redundant.bounds))<1e-6
assert set(tuple(v) for v in np.round(redundant.vertices,5)).issubset(set(tuple(v) for v in np.round(parent.vertices,5)))
# Same-colour overlay, not a separate painted road marking.
assert np.array_equal(np.unique(parent.visual.vertex_colors,axis=0),np.unique(redundant.visual.vertex_colors,axis=0))
# Check surface CONTAINMENT, not just congruent bounding boxes or shared vertices.
tri=redundant.triangles
pts=np.concatenate([tri.mean(axis=1),tri[:,0]*.6+tri[:,1]*.3+tri[:,2]*.1,
                    tri[:,0]*.1+tri[:,1]*.6+tri[:,2]*.3])
_,distance,_=trimesh.proximity.closest_point_naive(parent,pts)
maxerr=float(distance.max());assert maxerr<1e-6,maxerr

# Preserve every remaining original source node, transform, face and original vertex colour.
active=trimesh.Scene();quarantine=trimesh.Scene()
for n in s.graph.nodes_geometry:
 tf,k=s.graph[n]
 scene=quarantine if n==DUP else active
 scene.add_geometry(s.geometry[k].copy(),node_name=n,geom_name=n,transform=tf)
assert len(active.graph.nodes_geometry)==1346
assert sum(len(g.faces) for g in active.geometry.values())==691593
(O/'BNBU_v84_FULL_EDITABLE.glb').write_bytes(active.export('glb'))
(O/'BNBU_v84_REDUNDANT_ROAD000_SIDE_DISPLAY_ONLY.glb').write_bytes(quarantine.export('glb'))
# Diagnostic selection (exact parent source geometry, not a new road)
q=trimesh.Scene();q.add_geometry(parent.copy(),node_name=BASE,geom_name=BASE,transform=s.graph[BASE][0])
(O/'BNBU_v84_ROAD000_RETAINED_ONLY.glb').write_bytes(q.export('glb'))
for ext in ('gpkg','geojson','kml'):
 inputfile=I/f'BNBU_v83_{"EDITABLE_GIS" if ext=="gpkg" else "ACTIVE"}.{ext}'
 shutil.copy2(inputfile,D/f'BNBU_v84_{"EDITABLE_GIS" if ext=="gpkg" else "ACTIVE"}.{ext}')
report={
 'version':'v84','parent':'v83','parent_meshes':1347,'active_meshes':1346,
 'original_parent_faces':691907,'active_faces':691593,
 'removed_only_node':DUP,'same_position_parent':BASE,'removed_faces':314,
 'retained_parent_road_faces':416,'original_base_road_unchanged':True,
 'max_3d_distance_of_942_interior_samples_to_parent_road_m':maxerr,
 'same_vertex_colors':True,'same_scene_transforms':True,
 'remove_only_render_duplicate_not_a_real_road':True,
 'all_other_mesh_nodes_preserved_verbatim':1346,
 'changed_coordinates':0,'new_roads':0,'new_windows':0,'new_rails':0,'new_trees':0,
 'new_roof_equipment':0,'model_z_is_relative':True,'no_surveyed_source':True,
 'coordinate_frame':'GLB XY EPSG:32649 offset (758940,2474080); Z relative, GIS EPSG:4326',
 'record':'V42 FACET SIDE ROAD_000 is fully coincident with 416-face ROAD_000 solid, same RGBA; moving it to display-only avoids duplicate coplanar faces and preserves all existing physical road geometry.',
 'model_sha256':hashlib.sha256((O/'BNBU_v84_FULL_EDITABLE.glb').read_bytes()).hexdigest(),
 'parent_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),
}
(Q/'v84_geometry_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))