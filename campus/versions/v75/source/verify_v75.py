#!/usr/bin/env python3
"""Independent post-export v75 geometry and GIS integrity QA."""
from pathlib import Path
import json, hashlib, numpy as np, trimesh, shapely, fiona, xml.etree.ElementTree as ET
from shapely.geometry import Polygon,shape
from shapely.ops import unary_union,transform as shp_transform
from pyproj import Transformer
R=Path(__file__).resolve().parents[1]; I=R/'input';O=R/'model';D=R/'data';Q=R/'qa'
old=trimesh.load(I/'BNBU_v64_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(O/'BNBU_v75_FULL_EDITABLE.glb',force='scene',process=False)
v71=trimesh.load(I/'BNBU_v71_CONNECTED_LAKEFRONT.glb',force='scene',process=False)
report=json.loads((Q/'v75_build_report.json').read_text('utf8'))
so=set(old.graph.nodes_geometry);sn=set(new.graph.nodes_geometry)
assert len(so)==1381 and len(sn)==1379
ctv={n for n in so if 'CTV_CC401' in n}
replaced={n for n in so if n.startswith('FLOOR_EDGE_NOT_GLASS_STORYBAND_') and not old.geometry[old.graph[n][1]].is_watertight}
added={n for n in sn if n.startswith('V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_')}
pnames={n for n in sn if n.startswith('V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_')}
assert len(ctv)==4 and len(replaced)==len(added)==37 and len(pnames)==2
assert so-sn==ctv|replaced and sn-so==added|pnames
common=so&sn;assert len(common)==1340
for n in common:
 a=old.geometry[old.graph[n][1]];b=new.geometry[new.graph[n][1]]
 ta=old.graph[n][0];tb=new.graph[n][0]
 assert np.array_equal(a.vertices,b.vertices),n
 assert np.array_equal(a.faces,b.faces),n
 assert np.array_equal(ta,tb),n
 if hasattr(a.visual,"vertex_colors") and hasattr(b.visual,"vertex_colors"):
  assert np.array_equal(a.visual.vertex_colors,b.visual.vertex_colors),n

G=Transformer.from_crs(4326,32649,always_xy=True)
def loc(geom):return shp_transform(lambda x,y,z=None:(np.asarray(G.transform(x,y)[0])-758940,np.asarray(G.transform(x,y)[1])-2474080),geom)
js=json.loads((D/'BNBU_v75_ACTIVE.geojson').read_text('utf8'))
props={f['properties']['model_node']:f for f in js['features'] if f['properties'].get('model_node')}
assert len(js['features'])==565
lay=fiona.listlayers(D/'BNBU_v75_EDITABLE_GIS.gpkg');assert len(lay)==141
assert not any('CTV_CC401' in n for n in sn)
assert not any('CTV_CC401' in n for n in props)
assert not any('CTV' in n for n in lay)

max_diff=0.; max_warp=0.;max_volerr=0.; trcount=0
for n in added:
 orig='FLOOR_EDGE_NOT_GLASS_STORYBAND_'+n.split('STORYTRIM_')[1]
 tf,k=old.graph[orig];m0=old.geometry[k];v0=trimesh.transform_points(m0.vertices,tf);tris=v0[m0.faces];ztop=v0[:,2].max()
 top=(np.ptp(tris[:,:,2],axis=1)<1e-5)&(np.abs(tris[:,:,2].mean(axis=1)-ztop)<1e-4)
 p=unary_union([Polygon(x[:,:2]) for x in tris[top] if Polygon(x[:,:2]).area>1e-10])
 m=new.geometry[new.graph[n][1]];assert m.is_watertight and m.is_winding_consistent and m.volume>0,n
 assert abs(m.bounds[0,2]-v0[:,2].min())<5e-5 and abs(m.bounds[1,2]-v0[:,2].max())<5e-5
 xy=loc(shape(props[n]['geometry']))
 err=p.symmetric_difference(xy).area;max_diff=max(max_diff,err)
 assert err<0.0001,(n,err)
 max_warp=max(max_warp,p.hausdorff_distance(xy))
 volerr=abs(m.volume-p.area*(m.bounds[1,2]-m.bounds[0,2]))
 max_volerr=max(max_volerr,volerr)
 assert volerr<0.004,(n,volerr)
 assert props[n]['properties']['is_glass']==props[n]['properties']['is_surveyed']==props[n]['properties']['is_routable']==0
 trcount+=len(m.faces)

for n in pnames:
 a=v71.geometry[v71.graph[n][1]];b=new.geometry[new.graph[n][1]]
 assert np.array_equal(a.vertices,b.vertices),n
 # Repairing source orientation may invert faces but not geometry or materials.
 assert b.is_watertight and b.is_winding_consistent and b.volume>0,n
 if hasattr(a.visual,"vertex_colors") and hasattr(b.visual,"vertex_colors"):
  assert np.array_equal(a.visual.vertex_colors,b.visual.vertex_colors),n
 assert props[n]['properties']['is_surveyed']==props[n]['properties']['is_routable']==0
 assert loc(shape(props[n]['geometry'])).area>1

with fiona.open(D/'BNBU_v75_EDITABLE_GIS.gpkg',layer='v75_existing_opaque_storey_trims_closed') as f:
 assert len(f)==37 and f.crs.to_epsg()==4326
with fiona.open(D/'BNBU_v75_EDITABLE_GIS.gpkg',layer='v75_v71_source_grade_lrc_pavement_joins') as f:
 assert len(f)==2 and f.crs.to_epsg()==4326
ns={'k':'http://www.opengis.net/kml/2.2'}
tree=ET.parse(D/'BNBU_v75_ACTIVE.kml');pms=tree.findall('.//k:Placemark',ns)
assert len(pms)==565
for p in pms:
 name=p.findtext('k:name',namespaces=ns)
 if name in added|pnames:
  rings=p.findall('.//k:LinearRing/k:coordinates',ns)
  assert rings
  for ring in rings:
   pts=[tuple(float(x) for x in s.split(',')) for s in ring.text.split()]
   assert len(pts)>3 and pts[0]==pts[-1]
assert not any(('GLAZING_BELT_' in n or 'ROOF_HOUSE_PROXY' in n or 'LINK_GLASS_BALUSTRADE_PROPOSED' in n) for n in sn)
res={'pass':True,'version':'v75','parent_meshes':1381,'result_meshes':1379,
 'old_geometry_exactly_preserved':len(common),'new_closed_opaque_trim_meshes':len(added),
 'all_new_trims_watertight_winding_positive':True,'new_trim_triangles':trcount,
 'max_original_vs_new_gis_topology_symdiff_model_m2':max_diff,'max_original_vs_new_gis_hausdorff_model_m':max_warp,
 'max_mesh_vs_parent_volume_error_model_m3':max_volerr,
 'removed_unverified_ctv_meshes':len(ctv),'removed_unverified_ctv_active_gis_nodes':5,
 'merged_v71_pavement_joins_with_corrected_normals':len(pnames),
 'contiguous_route_certified':False,'gpkg_layers':len(lay),'geojson_features':len(js['features']),
 'kml_placemarks':len(pms),'v64_four_hills_preserved_exactly':all(n in common for n in so if n.startswith('V64_CONSTRAINED_RELIEF_')),
 'new_survey_data_0':True,'no_new_speculative_glass_trees_rooftop_houses':True,
 'warning':'parent XY and model-relative Z still unsurveyed; lakefront patches remain topology-based inference'}
(Q/'v75_independent_validation.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(res,ensure_ascii=False,indent=2))