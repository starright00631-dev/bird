#!/usr/bin/env python3
"""Independently load edited GLB & GIS and test changed and inherited geometry."""
from pathlib import Path
import json, numpy as np, trimesh, fiona, shapely
from shapely.geometry import shape, Point
from shapely.ops import transform
from pyproj import Transformer
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]; I=R/'input'; O=R/'model'; D=R/'data';Q=R/'qa'
old=trimesh.load(I/'BNBU_v76_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(O/'BNBU_v77_FULL_EDITABLE.glb',force='scene',process=False)
rep=json.loads((Q/'v77_build.json').read_text())
assert len(old.graph.nodes_geometry)==1380 and len(new.graph.nodes_geometry)==1382
cap=rep['modified_existing_cap_node']; names=[n for n in new.graph.nodes_geometry if n.startswith('V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_')]
assert len(names)==2
orig=set(old.graph.nodes_geometry); final=set(new.graph.nodes_geometry)
assert final-orig==set(names) and orig-final==set()
for n in orig-{cap}:
 ta,ka=old.graph[n]; tb,kb=new.graph[n];a=old.geometry[ka];b=new.geometry[kb]
 assert np.array_equal(a.vertices,b.vertices),n
 assert np.array_equal(a.faces,b.faces),n
 assert np.array_equal(ta,tb),n
 if hasattr(a.visual,"vertex_colors") and hasattr(b.visual,"vertex_colors"):
  assert np.array_equal(a.visual.vertex_colors,b.visual.vertex_colors),n
 else:
  assert type(a.visual)==type(b.visual),n
assert len(orig-{cap})==1379

def world(sc,n):
 t,k=sc.graph[n];m=sc.geometry[k].copy();m.apply_transform(t);return m
oc=world(old,cap);nc=world(new,cap)
diff=nc.vertices-oc.vertices
assert np.max(np.abs(diff[:,:2]))<1e-7
assert np.max(np.abs(diff[:,2]-rep['cap_relative_z_contact_correction_m']))<2e-6
assert np.array_equal(oc.faces,nc.faces)
pav=world(old,'V58_P2_ROUND_COMMONS_SQUARE_INLAID_ROOF_FIELD_PHOTO_TYPE_UNSURVEYED')
cap_gap=float(nc.bounds[0,2]-pav.bounds[1,2]);assert abs(cap_gap+.006)<2e-6,cap_gap
assert np.max(np.linalg.norm(nc.vertices[:,:2]-oc.vertices[:,:2],axis=1))<1e-7
assert nc.is_watertight and nc.is_winding_consistent
meshes=[world(new,n) for n in names]
assert all(m.is_watertight and m.is_winding_consistent and m.volume>0 for m in meshes)
assert sum(len(m.faces) for m in meshes)==320
assert all(m.bounds[0,2]>pav.bounds[1,2] for m in meshes)
full=trimesh.load(O/'BNBU_v77_PHASEII_ROOF_EDIT_ONLY.glb',force='scene',process=False)
assert len(full.graph.nodes_geometry)==3
# Georeferenced XY footprints for all new geometry must match GLB surfaces.
f=json.loads((D/'BNBU_v77_ACTIVE.geojson').read_text())
assert len(f['features'])==569
rec={r['properties']['model_node']:r for r in f['features'][-3:]};assert set(rec)=={cap,*names}
cr=Transformer.from_crs(4326,32649,always_xy=True)
def local(p):return transform(lambda x,y,z=None:(np.asarray(cr.transform(x,y)[0])-758940,np.asarray(cr.transform(x,y)[1])-2474080),p)
from shapely.geometry import Polygon
from shapely.ops import unary_union
errs=[]
for n in names:
 g=meshes[names.index(n)];zmax=g.bounds[1,2];faces=g.vertices[g.faces]
 top=(np.ptp(faces[:,:,2],axis=1)<1e-5)&(np.abs(faces[:,:,2].mean(axis=1)-zmax)<1e-4)
 hull=unary_union([Polygon(tr[:,:2]) for tr in faces[top]])
 gg=local(shape(rec[n]['geometry']))
 err=float(hull.symmetric_difference(gg).area); errs.append(err)
 assert err<0.003,(n,err)
 assert rec[n]['properties']['is_surveyed']==0 and rec[n]['properties']['is_glass']==0 and rec[n]['properties']['metric_birdstrike_eligible']==0
pg=local(shape(rec[cap]['geometry']));assert pg.centroid.distance(Point(nc.bounds.mean(axis=0)[:2]))<1e-4
layers=fiona.listlayers(D/'BNBU_v77_EDITABLE_GIS.gpkg');assert len(layers)==143
with fiona.open(D/'BNBU_v77_EDITABLE_GIS.gpkg',layer='v77_p2_roof_disk_contact_and_paver_seams_unsurveyed') as layer:
 assert len(layer)==3 and layer.crs.to_epsg()==4326
 for obj in layer:
  nm=obj['properties']['model_node'];assert nm in rec
  assert local(shape(obj['geometry'])).symmetric_difference(local(shape(rec[nm]['geometry']))).area<1e-5
ns={'k':'http://www.opengis.net/kml/2.2'}
root=ET.parse(D/'BNBU_v77_ACTIVE.kml').getroot()
pms=root.findall('.//k:Placemark',ns);assert len(pms)==569
assert {e.find('k:name',ns).text for e in pms[-3:]}==set(rec)
for p in pms[-3:]:
 for x in p.findall('.//k:LinearRing/k:coordinates',ns):
  ll=x.text.split();assert len(ll)>=4 and ll[0]==ll[-1]
for n in final:
 assert not any(q in n for q in ['GLAZING_BELT_','LINK_GLASS_BALUSTRADE_PROPOSED','ROOF_HOUSE_PROXY'])
assert not any('GLASS' in n for n in names)
report={'version':'v77','pass':True,'GLB_nodes':1382,'unchanged_parent_GLBS_exact_mesh_vertices_faces_transforms_colors':1379,'cap_unchanged_XY_faces':True,'cap_adjustment_z_model_m':rep['cap_relative_z_contact_correction_m'],'post_repair_cap_gap_above_paver_model_m':cap_gap,'new_watertight_opaque_seam_groups':2,'new_triangle_count':320,'max_seam_GIS_GLB_symmetric_difference_m2':max(errs),'gpkg_layers':len(layers),'geojson_features':len(f['features']),'kml_placemarks':len(pms),'not_surveyed':True,'no_new_GLASS_or_random_trees_or_guessed_roof_machinery':True,'warning':'Photo-grounded seam presence; seam coordinates and count approximated without image registration or in-situ survey.'}
(Q/'v77_independent_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))