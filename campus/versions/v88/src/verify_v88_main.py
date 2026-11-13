#!/usr/bin/env python3
import json, hashlib, base64
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'history'/'BNBU_v71_CONNECTED_LAKEFRONT_v76_parent.glb'
G=ROOT/'generated'/'BNBU_v71_CONNECTED_LAKEFRONT.glb'
AT=ROOT/'generated'/'BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json'
def active_triangles(s):
    keys={s.graph[n][1] for n in s.graph.nodes_geometry}
    return sum(len(s.geometry[k].faces) for k in keys)
parent=trimesh.load(P,force='scene',process=False); clean=trimesh.load(G,force='scene',process=False)
assert len(parent.graph.nodes_geometry)==1379 and active_triangles(parent)==659793
assert len(clean.graph.nodes_geometry)==1378 and active_triangles(clean)==659479
assert 'V42_FACET_SIDE_ROAD_000' not in clean.graph.nodes_geometry and 'ROAD_000' in clean.graph.nodes_geometry
changed=[]
for n in clean.graph.nodes_geometry:
    t0,k0=parent.graph[n];t1,k1=clean.graph[n]
    a=parent.geometry[k0];b=clean.geometry[k1]
    if not (np.array_equal(t0,t1) and np.array_equal(a.vertices,b.vertices) and np.array_equal(a.faces,b.faces)): changed.append(n)
assert not changed,changed[:10]
atlas=json.loads(AT.read_text('utf-8'))
assert atlas['building_count']==30 and len(atlas['extended_records'])==8
assert len(atlas['building_records'])+len(atlas['extended_records'])==38
reg=json.loads((ROOT/'registry'/'BNBU_v88_BUILDING_ASSET_REGISTRY.json').read_text('utf-8'))
assert reg['scope']['mapped_asset_records']==38 and reg['scope']['unmapped_official_assets']==1 and reg['scope']['quarantined_hypotheses']==1
viewer=(ROOT/'viewer.js').read_text('utf-8'); assert 'it.length!==1378' in viewer and 'v88MappedAssetCount' in viewer
html=(ROOT/'双击查看_校园3D.html').read_text('utf-8')
tag='<script id="embedded-v71" type="application/octet-stream">';st=html.index(tag)+len(tag);en=html.index('</script>',st)
assert hashlib.sha256(base64.b64decode(html[st:en])).hexdigest()==hashlib.sha256(G.read_bytes()).hexdigest()
print(json.dumps({'pass':True,'active_mesh_nodes':1378,'active_triangles':659479,'unchanged_common_nodes':1378,'core_buildings':30,'extended_mapped_assets':8,'mapped_assets':38},ensure_ascii=False,indent=2))