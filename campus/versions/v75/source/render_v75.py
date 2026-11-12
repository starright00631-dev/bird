#!/usr/bin/env python3
"""Actual parent/output GLB triangle rendering; not a GIS sketch or orthophoto."""
from pathlib import Path
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
R=Path(__file__).resolve().parents[1];F=R/'figures';F.mkdir(exist_ok=True)
old=trimesh.load(R/'input/BNBU_v64_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(R/'model/BNBU_v75_FULL_EDITABLE.glb',force='scene',process=False)
def mesh(s,n):
 tf,k=s.graph[n];m=s.geometry[k];return trimesh.Trimesh(vertices=trimesh.transform_points(m.vertices,tf),faces=m.faces,process=False)
def draw(ax, m, c, alpha=.85, outline=True, exaggerate=1):
 f=m.vertices[m.faces].copy()
 # Relative vertical exaggeration improves legibility; not survey values
 low=m.bounds[0,2];f[:,:,2]=(f[:,:,2]-low)*exaggerate+low
 face=Poly3DCollection(f,alpha=alpha,linewidths=.26 if outline else 0,edgecolor='#5d7481' if outline else None)
 face.set_facecolor(c);ax.add_collection3d(face)
 return np.concatenate([f.reshape(-1,3)],axis=0)
def setup(ax, pts, title, view=(37,-65)):
 a=np.vstack(pts);lo=a.min(axis=0);hi=a.max(axis=0);mid=(lo+hi)/2
 delta=np.maximum(hi-lo,[1,1,1]);d=max(delta[0],delta[1])
 ax.set(xlim=(mid[0]-d*.62,mid[0]+d*.62),ylim=(mid[1]-d*.62,mid[1]+d*.62),zlim=(mid[2]-d*.15,mid[2]+d*.25))
 ax.view_init(elev=view[0],azim=view[1]);ax.set_title(title,fontsize=10,pad=7)
 ax.set_xticks([]);ax.set_yticks([]);ax.set_zticks([]);ax.set_box_aspect([1,1,.25]);ax.set_facecolor('#eef4f6')
for name in ['V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_01_NOT_SURVEYED','V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_02_NOT_SURVEYED']:
 assert name in new.graph.nodes_geometry and name not in old.graph.nodes_geometry
fig=plt.figure(figsize=(16,11),dpi=150)
fig.patch.set_facecolor('white')
# First row: existing structural story edge topology repair
oldname='FLOOR_EDGE_NOT_GLASS_STORYBAND_V15_3_0'
newname='V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_V15_3_0'
for j,(s,n,title,c) in enumerate([(old,oldname,'v64 · V15 old open-edge slab','#e0a5a1'),(new,newname,'v75 · V15 repaired closed solid','#70b0a0')]):
 ax=fig.add_subplot(3,2,j+1,projection='3d');m=mesh(s,n);pts=[draw(ax,m,c,exaggerate=22)];setup(ax,pts,title)
# 2nd row: LRC shore promenade with two actual patch mesh solids
refnames=['V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_01_UNSURVEYED',
 'V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_02_UNSURVEYED',
 'V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_03_UNSURVEYED']
for j,s in enumerate([old,new]):
 ax=fig.add_subplot(3,2,3+j,projection='3d');pts=[]
 for n in refnames:
  if n in s.graph.nodes_geometry:pts.append(draw(ax,mesh(s,n),'#b4c5c5',.92,True,4))
 if j:
  for n in new.graph.nodes_geometry:
   if n.startswith('V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_'):
    pts.append(draw(ax,mesh(s,n),'#dc9560',1,True,4))
 setup(ax,pts,'v64 · inherited promenade gaps' if not j else 'v75 · two sourced, unsurveyed grade joints',view=(48,-75))
# Third row: CTV speculative small house removed from active campus model
ctvnames=[n for n in old.graph.nodes_geometry if 'CTV_CC401' in n]
for j,s in enumerate([old,new]):
 ax=fig.add_subplot(3,2,5+j,projection='3d');pts=[]
 # Nearby unmodified walk for geographic context
 for n in s.graph.nodes_geometry:
  if n.startswith('V54_PAVEMENT_SEAM_CLOSE_ROAD_000__WALK_040'):
   pts.append(draw(ax,mesh(s,n),'#b4c5c5',.85))
 if j==0:
  for n in ctvnames:pts.append(draw(ax,mesh(s,n),'#d88a83',.95))
 else:
  # Dummy ground reference is not drawn; use original CTV extents for camera framing only
  for n in ctvnames:pts.append(mesh(old,n).vertices)
 setup(ax,pts,'v64 · unverified CTV house in active GLB' if not j else 'v75 · removed to separate quarantine GLB',view=(43,-67))
fig.text(.5,.015,'GLB vertex/triangle comparison. Model-relative Z; v15 vertical exaggerated 22×. No orthophoto registration or field survey.',ha='center',fontsize=11,color='#566779')
plt.subplots_adjust(left=.01,right=.99,top=.96,bottom=.06,wspace=.02,hspace=.13)
fig.savefig(F/'BNBU_v75_actual_GLB_before_after.png',dpi=150)
plt.close(fig)
print((F/'BNBU_v75_actual_GLB_before_after.png').stat().st_size)