#!/usr/bin/env python3
"""Visual compare read from ORIGINAL and EXPORTED real GLB triangle meshes."""
from pathlib import Path
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
R=Path(__file__).resolve().parents[1]
a=trimesh.load(R/'input'/'BNBU_v63_FULL_EDITABLE.glb',force='scene',process=False)
b=trimesh.load(R/'model'/'BNBU_v64_FULL_EDITABLE.glb',force='scene',process=False)
items=[('EAST_ARTS_HILL_NON_SURVEYED','East arts hill'),('NORTH_RIDGE_NON_SURVEYED','North ridge'),('PHASEII_WEST_HILL_NON_SURVEYED','Phase II west hill'),('WEST_WOODLAND_SLOPE_NON_SURVEYED','Woodland slope')]
fig,axs=plt.subplots(4,2,figsize=(12,18),constrained_layout=True,facecolor='white')
for i,(suffix,label) in enumerate(items):
 for j,(scene,prefix) in enumerate([(a,'V53_TERRAIN_RELIEF_'),(b,'V64_CONSTRAINED_RELIEF_')]):
  name=prefix+suffix;tf,k=scene.graph[name];m=scene.geometry[k]
  verts=trimesh.transform_points(m.vertices,tf)
  mask=(m.face_normals[:,2]>.08) & (verts[m.faces].mean(axis=(1,2))>-999)
  faces=m.faces[mask];tris=verts[faces]
  use=(np.ptp(tris[:,:,2],axis=1)>0.015) | (tris[:,:,2].mean(axis=1)>.3)
  tris=tris[use]
  # Exact triangles of the loaded GLB, with deterministic decimation for raster speed.
  skip=max(1,len(tris)//8000); tris=tris[::skip]
  coll=PolyCollection(tris[:,:,:2],array=np.mean(tris[:,:,2],axis=1),cmap='terrain',edgecolors='none',norm=Normalize(vmin=-.2,vmax=10))
  ax=axs[i,j];ax.add_collection(coll);ax.autoscale_view();ax.set_aspect('equal');ax.tick_params(labelsize=7)
  ax.set_title(label+' / '+('v63 parent' if j==0 else 'v64 smoothed Z'),fontsize=11)
  if i==3:ax.set_xlabel('Local X in model metres')
  ax.set_ylabel('Local Y in model metres')
fig.colorbar(ScalarMappable(norm=Normalize(vmin=-.2,vmax=10),cmap='terrain'),ax=axs,shrink=.38,label='Model-relative Z (not real elevation)')
fig.savefig(R/'figures'/'BNBU_v64_terrain_actual_GLB_before_after.png',dpi=160)
plt.close(fig)
# One 3D paired render of exact mesh triangles to distinguish this from a flat GIS workbench.
fig=plt.figure(figsize=(15,6),facecolor='white')
for j,(scene,prefix) in enumerate([(a,'V53_TERRAIN_RELIEF_'),(b,'V64_CONSTRAINED_RELIEF_')]):
 name=prefix+'NORTH_RIDGE_NON_SURVEYED';tf,k=scene.graph[name];m=scene.geometry[k];v=trimesh.transform_points(m.vertices,tf)
 triangles=v[m.faces[m.face_normals[:,2]>.08]]
 triangles=triangles[::max(1,len(triangles)//4500)]
 ax=fig.add_subplot(1,2,j+1,projection='3d')
 val=triangles[:,:,2].mean(axis=1);norm=Normalize(vmin=0,vmax=10)
 ax.add_collection3d(Poly3DCollection(triangles,facecolors=plt.get_cmap('terrain')(norm(val)),edgecolors='none',linewidths=0))
 ax.set_xlim(v[:,0].min(),v[:,0].max());ax.set_ylim(v[:,1].min(),v[:,1].max());ax.set_zlim(-.2,12)
 ax.view_init(elev=24,azim=-72);ax.set_box_aspect([3,1,0.5]);ax.tick_params(labelsize=7)
 ax.set_title('North ridge | '+('v63 inherited faces' if j==0 else 'v64 altered vertices, identical faces'),fontsize=11)
fig.savefig(R/'figures'/'BNBU_v64_NorthRidge_real_GLB_3D.png',dpi=160,bbox_inches='tight')
plt.close(fig)