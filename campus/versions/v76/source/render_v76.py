#!/usr/bin/env python3
"""Actual GLB triangle comparison, not a tracing of the hand-drawn campus image."""
from pathlib import Path
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
R=Path(__file__).resolve().parents[1];F=R/'figures';F.mkdir(parents=True,exist_ok=True)
old=trimesh.load(R/'input/BNBU_v75_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(R/'model/BNBU_v76_FULL_EDITABLE.glb',force='scene',process=False)
names=['ROOF_DECK_LRC','LRC_SKYLIGHT_RIM','V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_EASTWEST','V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_NORTHSOUTH']
added='V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED'
def get(s,n):
 tf,k=s.graph[n];m=s.geometry[k].copy();m.apply_transform(tf);return m
fig=plt.figure(figsize=(14.5,7.2),dpi=145)
colors={'ROOF_DECK_LRC':('#e5dac5',1.0,4), 'LRC_SKYLIGHT_RIM':('#e9b56d',1.,1),
 'V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_EASTWEST':('#646f75',1,4),
 'V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_NORTHSOUTH':('#64737a',1,4),
 added:('#73c9de',.65,9)}
for j,scene in enumerate([old,new]):
 ax=fig.add_subplot(1,2,j+1,projection='3d');ax.set_facecolor('#f1f7f8')
 for n in names+([added] if j else []):
  m=get(scene,n);color,alpha,stride=colors[n]
  tris=m.vertices[m.faces][::stride].copy()
  # show inherited geometric relief at 1:1.15 Z scale for visualization only
  tris[:,:,2]=17.0+1.2*(tris[:,:,2]-17.0)
  pc=Poly3DCollection(tris,facecolors=color,alpha=alpha,edgecolor='none',linewidth=0,zsort='average')
  ax.add_collection3d(pc)
 ax.set(xlim=(135,173),ylim=(-91,-53),zlim=(16.7,23),xlabel='',ylabel='',zlabel='')
 ax.set_xticks([]);ax.set_yticks([]);ax.set_zticks([]);ax.set_box_aspect((1,1,.26));ax.view_init(elev=36,azim=-59)
 ax.set_title('v75 · skylight rim and ribs, no glass infill' if not j else 'v76 · single continuous curved glass infill',size=11)
fig.text(.5,.035,'Source XY: inherited v75 LRC roof opening | Source curvature: inherited v75 arched mullions | NOT orthophoto or surveyed glass area',ha='center',fontsize=10,color='#4a6673')
fig.tight_layout(rect=(.02,.07,.98,.98))
out=F/'BNBU_v76_LRC_actual_GLB_before_after.png';fig.savefig(out,dpi=145,facecolor='white');plt.close(fig)
print('Wrote',out,out.stat().st_size)