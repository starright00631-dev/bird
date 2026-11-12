from pathlib import Path
import sys,json,trimesh
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'viewer'))
from make_viewer import generate
src=trimesh.load(R/'model/BNBU_v75_FULL_EDITABLE.glb',force='scene',process=False)
s=trimesh.Scene();keep=[]
for n in src.graph.nodes_geometry:
 if n.startswith('V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_') or n.startswith('V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_') or n.startswith('V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_'):
  tf,k=src.graph[n];s.add_geometry(src.geometry[k].copy(),node_name=n,geom_name=n,transform=tf);keep.append(n)
assert len(keep)==42
(R/'model'/'BNBU_v75_CHANGESET_AND_LRC_CONTEXT.glb').write_bytes(s.export('glb'))
# Own copy of full offline viewer code, smaller embedded scene for rendering QA.
t=(R/'viewer'/'viewer_template_v75.html').read_text('utf8')
t=t.replace('BNBU 校园三维模型查看器','BNBU v75 改动局部三维查看器')
t=t.replace('BNBU / CAMPUS ATLAS','BNBU / GEOMETRY DELTA')
t=t.replace('校园完整模型','37 个结构层饰带 + 2 个小铺装连接（3 个 LRC 既有板仅作对照）')
(R/'viewer'/'viewer_template_v75_delta.html').write_text(t,'utf8')
generate(R/'model'/'BNBU_v75_CHANGESET_AND_LRC_CONTEXT.glb',R/'BNBU_v75_Changes_3D_Viewer.html','v75-delta',R/'viewer'/'viewer_template_v75_delta.html')
print('delta_nodes',len(keep))