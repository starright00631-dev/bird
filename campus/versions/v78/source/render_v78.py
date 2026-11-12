#!/usr/bin/env python3
"""Render before/after directly from source GLB triangles; no synthetic architecture."""
from pathlib import Path
import json,numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
R=Path(__file__).resolve().parent;O=R/'figures';O.mkdir(exist_ok=True)
a=trimesh.load(R/'input/main_v71.glb',force='scene',process=False);b=trimesh.load(R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb',force='scene',process=False)
r=json.loads((R/'qa/v78_geometry_compatibility.json').read_text())['source_main_name_to_branch_replacements'];pairs=list(r.items())
fig=plt.figure(figsize=(15,5.7),facecolor='white');axs=[]
for i in range(3):axs.append(fig.add_subplot(1,3,i+1,projection='3d'))
sel=pairs[:14];oldlist=[x for x,y in sel];newlist=[y for x,y in sel]
def draw(ax,sc,names,facecolor,cap=2600):
 allp=[];total=0
 for name in names:
  tf,key=sc.graph[name];mesh=sc.geometry[key];verts=trimesh.transform_points(mesh.vertices,tf);tri=verts[mesh.faces]
  if len(tri)>8000:tri=tri[::max(1,int(len(tri)//6000))]
  if len(tri)+total>cap and len(names)>1:tri=tri[::max(1,int((len(tri)+total)/cap))]
  if len(tri):
   ax.add_collection3d(Poly3DCollection(tri,alpha=.87,facecolor=facecolor,edgecolor='#344f61',linewidth=.22));allp.append(verts);total+=len(tri)
 if allp:
  data=np.concatenate(allp)
  for j,lims in enumerate([[data[:,j].min(),data[:,j].max()] for j in range(3)]):
   d=max(lims[1]-lims[0],1);lim=(lims[0]+lims[1])/2
   (ax.set_xlim,ax.set_ylim,ax.set_zlim)[j](lim-d*.55,lim+d*.55)
  ax.set_box_aspect((1,1,.40),zoom=.88)
 ax.view_init(elev=40,azim=-66);ax.grid(False);ax.set_xticks([]);ax.set_yticks([]);ax.set_zticks([])
for ax,names,sc,color,title in [(axs[0],oldlist,a,'#d8aa90','main v71: original open opaque trims'),(axs[1],newlist,b,'#6cafa9','v78: exact-footprint closed solids')]:
 draw(ax,sc,names,color);ax.set_title(title,fontsize=11)
sky=[n for n in b.graph.nodes_geometry if n.startswith('V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS')]
assert len(sky)==1
draw(axs[2],b,sky,'#5ca1c9',cap=6000);axs[2].set_title('v78: LRC curved skylight\n(rib-constrained, unsurveyed)',fontsize=11)
fig.suptitle('BNBU 3D source GLB geometry reconciliation  |  No invented windows, roads, trees',fontsize=13,y=.99)
fig.text(.02,.03,'Left and middle: selected 14 of 37 existing floor-edge solids. Differences are topology, not photo registration. Right: inherited v76 skylight. Vertical scale exaggerated by panel.',fontsize=8)
fig.savefig(O/'BNBU_v78_actual_GLB_mesh_before_after.png',dpi=160,bbox_inches='tight');plt.close(fig)
print(O/'BNBU_v78_actual_GLB_mesh_before_after.png')