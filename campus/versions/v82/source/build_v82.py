#!/usr/bin/env python3
"""Targeted, evidence-safe mesh winding fix for two already-existing LRC grade joints.
No geometric coordinates, topology, materials, or confidence scores are invented.
Inherit v81 exact GLB. Retain v81 GIS geometries byte-for-byte, only rename artifacts.
"""
from pathlib import Path
import json, shutil
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'input'/'BNBU_v81_FULL_EDITABLE.glb'
OUT=ROOT/'model'/'BNBU_v82_FULL_EDITABLE.glb'
TARGETS=('V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_01_NOT_SURVEYED',
         'V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_02_NOT_SURVEYED')
s=trimesh.load(INPUT,force='scene',process=False)
assert len(s.graph.nodes_geometry)==1347
result=trimesh.Scene();changes=[];pair=trimesh.Scene()
for name in s.graph.nodes_geometry:
    transform, geom_key=s.graph[name]
    before=s.geometry[geom_key]
    after=before.copy()
    if name in TARGETS:
        assert len(before.faces)==12 and before.is_watertight and not before.is_winding_consistent and before.volume < 0
        old_tris=np.sort(before.faces,axis=1)
        after.fix_normals()
        assert after.is_watertight and after.is_winding_consistent and after.volume > 0
        assert np.array_equal(after.vertices,before.vertices)
        assert np.array_equal(np.sort(after.faces,axis=1),old_tris)
        assert after.visual.kind==before.visual.kind
        if after.visual.kind=="vertex": assert np.array_equal(after.visual.vertex_colors,before.visual.vertex_colors)
        if after.visual.kind=="texture": assert np.array_equal(after.visual.uv,before.visual.uv)
        flipped=int(np.sum(np.any(after.faces!=before.faces,axis=1)))
        changes.append({'node':name,'face_count':len(after.faces),'reoriented_faces':flipped,
          'old_signed_volume':float(before.volume),'new_signed_volume':float(after.volume),
          'local_bounds':before.bounds.tolist(),
          'vertex_delta_max':0,'area_before_model_m2':float(before.area),'area_after_model_m2':float(after.area),
          'model_Z_min':float(before.vertices[:,2].min()),'model_Z_max':float(before.vertices[:,2].max()),
          'source':'v81 exact existing geometry; v71 parent grade-joint construction',
          'confidence':'Inherited proxy, unregistered, unmeasured; winding fix only'})
        pair.add_geometry(after.copy(),node_name=name,geom_name=name,transform=transform)
    result.add_geometry(after,node_name=name,geom_name=name,transform=transform)
assert len(changes)==2
OUT.write_bytes(result.export('glb'))
(ROOT/'model'/'BNBU_v82_LRC_WINDING_FIXED_ONLY.glb').write_bytes(pair.export('glb'))
for suffix in ['EDITABLE_GIS.gpkg','ACTIVE.geojson','ACTIVE.kml','DISPLAY_ONLY.geojson','DISPLAY_ONLY.kml']:
    src=ROOT/'input'/('BNBU_v81_'+suffix)
    shutil.copy2(src,ROOT/'data'/('BNBU_v82_'+suffix))
rep={'version':'v82','parent':'v81','main_meshes':len(result.graph.nodes_geometry),'total_parent_faces':sum(len(s.geometry[s.graph[n][1]].faces) for n in s.graph.nodes_geometry),
 'changed_meshes':len(changes),'edited_triangles_total':sum(c['reoriented_faces'] for c in changes),
 'new_model_vertices':0,'new_model_faces':0,'new_osm_ways':0,'new_windows':0,'new_bridges':0,'new_roads':0,
 'glb_model_crs':'EPSG:32649 offset (758940,2474080), model relative Z',
 'gis_model_crs':'EPSG:4326, inherited v81 position; no orthophoto registration',
 'changes':changes}
(ROOT/'qa'/'v82_geometry_build.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),'utf8')
print(json.dumps(rep,indent=2,ensure_ascii=False))