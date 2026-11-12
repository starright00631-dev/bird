#!/usr/bin/env python3
"""Comparison from ACTUAL v76 and v77 GLB, not reconstructed illustration."""
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np,trimesh
R=Path(__file__).resolve().parents[1]
a=trimesh.load(R/'input/BNBU_v76_FULL_EDITABLE.glb',force='scene',process=False)
b=trimesh.load(R/'model/BNBU_v77_FULL_EDITABLE.glb',force='scene',process=False)
fig=plt.figure(figsize=(15.2,6.4),facecolor='#f9fafb')
for j,(sc,title) in enumerate([(a,'v76  |  inherited pavilion rooftop'),(b,'v77  |  roof contact repaired + paving seams')]):
 ax=fig.add_subplot(1,2,j+1,projection='3d',computed_zorder=False)
 nodes=[n for n in sc.graph.nodes_geometry if n.startswith('V24_P2_CIRCULAR_COMMONS_0') or n.startswith('V58_P2_ROUND_COMMONS_SQUARE_') or n.startswith('V58_P2_ROUND_COMMONS_OPAQUE_SQUARE_') or n.startswith('V77_P2_COMMONS_ROOF_')]
 colors={'V77_P2':'#53412f','V58_P2_ROUND_COMMONS_SQUARE_':'#e2dccb','V58_P2_ROUND_COMMONS_OPAQUE_SQUARE_':'#c4b8a2','V24_P2_CIRCULAR_COMMONS_09':'#a88b60','V24_P2_CIRCULAR_COMMONS_08':'#d7d1bb','V24_P2_CIRCULAR_COMMONS_07':'#c4b79b'}
 for n in sorted(nodes,key=lambda x:x.startswith('V77_')):
  if 'V24_P2_CIRCULAR_COMMONS_0' in n and not any(x in n for x in ('_07_','_08_','_09_')):continue
  tf,k=sc.graph[n];g=sc.geometry[k];v=trimesh.transform_points(g.vertices,tf)
  tris=v[g.faces];tris=tris[(tris[:,:,2].mean(axis=1)>7.24)]
  if len(tris)>2500:tris=tris[::max(1,len(tris)//2500)]
  col=next((c for key,c in colors.items() if n.startswith(key)),'#bfb8ab')
  alpha=0.98 if n.startswith('V77_') else .84
  p=Poly3DCollection(tris,facecolors=col,edgecolors='#47413b' if n.startswith('V77_') else 'none',linewidths=.12,alpha=alpha,zsort='average',zorder=15 if n.startswith('V77_') else 2)
  ax.add_collection3d(p)
 ax.set_xlim(-377,-344);ax.set_ylim(858,892);ax.set_zlim(7.0,9.3)
 ax.set_box_aspect((33,34,3.8),zoom=.91)
 ax.view_init(elev=62,azim=-61)
 ax.set_title(title,fontsize=12,fontweight='semibold',pad=13)
 ax.set_xlabel('Local East (model m)',fontsize=8);ax.set_ylabel('Local North (model m)',fontsize=8)
 ax.set_zticks([7.0,7.5,8.0]);ax.tick_params(labelsize=7)
 ax.grid(False)
 ax.xaxis.pane.set_alpha(.0);ax.yaxis.pane.set_alpha(.0);ax.zaxis.pane.set_alpha(.0)
fig.text(.5,.035,'Meshes read from original GLB files; seam count/spacing and vertical coordinate are NOT surveyed',ha='center',fontsize=10,color='#434d5a')
fig.tight_layout(rect=[0,.07,1,1])
out=R/'figures/BNBU_v77_pavilion_actual_GLB_before_after.png';out.parent.mkdir(exist_ok=True,parents=True)
fig.savefig(out,dpi=175,facecolor=fig.get_facecolor());print(out)