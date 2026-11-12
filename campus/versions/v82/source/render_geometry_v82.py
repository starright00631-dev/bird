#!/usr/bin/env python3
"""Actual before/after GLB triangles, normals indicate winding, Z exaggerated 5x (display only)."""
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np,trimesh
R=Path(__file__).resolve().parents[1]
a=trimesh.load(R/'input/BNBU_v81_FULL_EDITABLE.glb',force='scene',process=False)
b=trimesh.load(R/'model/BNBU_v82_FULL_EDITABLE.glb',force='scene',process=False)
names=['V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_01_NOT_SURVEYED','V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_02_NOT_SURVEYED']
fig=plt.figure(figsize=(13,6.5),facecolor='#f9fbfd')
for side,(title,s) in enumerate([('v81  ·  inconsistent inward side faces',a),('v82  ·  corrected outward winding',b)]):
 ax=fig.add_subplot(1,2,side+1,projection='3d');ax.set_facecolor('#f9fbfd')
 for idx,name in enumerate(names):
  tf,k=s.graph[name];m=s.geometry[k];v=trimesh.transform_points(m.vertices,tf)
  tris=v[m.faces].copy();tris[:,:,2]*=5
  col=['#d58b6e','#dba178'] if side==0 else ['#57ada8','#84bfc0']
  mesh=Poly3DCollection(tris,alpha=.72,linewidth=.65,edgecolor='#243d4b',facecolor=col[idx]);ax.add_collection3d(mesh)
  for j in [4,6,8,10]:
   c=tris[j].mean(axis=0);n=np.cross(tris[j][1]-tris[j][0],tris[j][2]-tris[j][0]);n=n/(np.linalg.norm(n)+1e-10)
   ax.quiver(*c,*(n*.44),color=('#c52d35' if side==0 else '#08776d'),arrow_length_ratio=.36,linewidth=1.3)
 xyz=[]
 for n in names:
  tf,k=s.graph[n];v=trimesh.transform_points(s.geometry[k].vertices,tf);v[:,2]*=5;xyz.append(v)
 v=np.concatenate(xyz);ax.set_xlim(183.5,200);ax.set_ylim(-98,-88);ax.set_zlim(0,2.5);ax.set_box_aspect((16,10,3.8))
 ax.set_xlabel('local X (model m)');ax.set_ylabel('local Y');ax.set_zlabel('relative Z ×5')
 ax.view_init(elev=25,azim=235);ax.set_title(title,fontsize=13,pad=18)
fig.suptitle('BNBU LRC lakeside · original v81 vs v82 GLB triangles (no coordinate edits)',fontsize=15,y=.98)
fig.text(.5,.03,'Only 16 side triangles had winding flipped. Local XY/Z unchanged; structures not surveyed.',ha='center',fontsize=10,color='#546b7a')
fig.tight_layout(rect=[0,.05,1,.93]);fig.savefig(R/'figures/BNBU_v82_actual_GLB_face_winding_before_after.png',dpi=165)