#!/usr/bin/env python3
"""Independent re-import, coordinate preservation, geometry/roof-hole and GIS consistency."""
from pathlib import Path
import json, xml.etree.ElementTree as ET
import numpy as np, trimesh, fiona
from shapely.geometry import Polygon,shape
from shapely.ops import transform as shapely_transform, unary_union
from pyproj import Transformer
R=Path(__file__).resolve().parents[1]; I=R/'input';O=R/'model';D=R/'data';Q=R/'qa'
p=trimesh.load(I/'BNBU_v75_FULL_EDITABLE.glb',force='scene',process=False)
s=trimesh.load(O/'BNBU_v76_FULL_EDITABLE.glb',force='scene',process=False)
name='V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED'
a=set(p.graph.nodes_geometry);b=set(s.graph.nodes_geometry)
assert len(a)==1379 and len(b)==1380 and b-a=={name} and a-b==set()
for n in a:
 t1,k1=p.graph[n];t2,k2=s.graph[n]
 m1=p.geometry[k1];m2=s.geometry[k2]
 assert np.array_equal(t1,t2),n
 assert np.array_equal(m1.vertices,m2.vertices),n
 assert np.array_equal(m1.faces,m2.faces),n
 def cv(mesh):
  return mesh.visual.vertex_colors if hasattr(mesh.visual,'vertex_colors') else mesh.visual.to_color().vertex_colors
 assert np.array_equal(cv(m1),cv(m2)),n
print('Unchanged meshes verified',len(a),flush=True)
t,k=s.graph[name];m=s.geometry[k];m.apply_transform(t)
assert len(m.faces)==34816 and m.is_watertight and m.is_winding_consistent and m.volume>0
assert np.isfinite(m.vertices).all() and m.bounds[1,2]>21.2
assert 'PBRMaterial' in str(type(m.visual.material)) and m.visual.material.alphaMode=='BLEND'
rim=p.geometry[p.graph['LRC_SKYLIGHT_RIM'][1]].copy();rim.apply_transform(p.graph['LRC_SKYLIGHT_RIM'][0]);tt=rim.vertices[rim.faces]
h=(np.ptp(tt[:,:,2],axis=1)<1e-5)
p_top=unary_union([Polygon(v[:,:2]) for v in tt[h] if Polygon(v[:,:2]).area>1e-8])
assert p_top.geom_type=='Polygon' and len(p_top.interiors)==1
boundary=Polygon(p_top.interiors[0]);area=boundary.area
assert abs(area-315.38228)<.01
roof=p.geometry[p.graph['ROOF_DECK_LRC'][1]].copy();roof.apply_transform(p.graph['ROOF_DECK_LRC'][0]);top=roof.vertices[roof.faces];mask=np.ptp(top[:,:,2],axis=1)<1e-5
roofprint=unary_union([Polygon(tr[:,:2]) for tr in top[mask] if Polygon(tr[:,:2]).area>1e-8])
assert boundary.difference(Polygon(roofprint.interiors[0])).area<1e-5
# No transparent roof surface over pre-existing solid roof, except shared seam.
assert Polygon(m.vertices[:len(m.vertices)//2,:2]).convex_hull.intersection(roofprint).area<1e-4
project=Transformer.from_crs(4326,32649,always_xy=True)
def local(g):return shapely_transform(lambda x,y,z=None:(np.asarray(project.transform(x,y)[0])-758940,np.asarray(project.transform(x,y)[1])-2474080),g)
gis=json.loads((D/'BNBU_v76_ACTIVE.geojson').read_text())
assert len(gis['features'])==566
feat=[f for f in gis['features'] if f['properties'].get('model_node')==name]
assert len(feat)==1 and feat[0]['properties']['metric_birdstrike_eligible']==0 and feat[0]['properties']['is_glass']==1
assert feat[0]['properties']['is_surveyed']==0 and feat[0]['properties']['is_routable']==0
pointset=local(shape(feat[0]['geometry']))
err=float(boundary.symmetric_difference(pointset).area)
assert err<0.0003,err
layers=fiona.listlayers(D/'BNBU_v76_EDITABLE_GIS.gpkg')
assert len(layers)==142 and 'v76_existing_LRC_atrium_skylight_glazing_nonmetric' in layers
with fiona.open(D/'BNBU_v76_EDITABLE_GIS.gpkg',layer='v76_existing_LRC_atrium_skylight_glazing_nonmetric') as f:
 assert len(f)==1 and f.crs.to_epsg()==4326
 gf=next(iter(f)); assert gf['properties']['model_node']==name
 assert local(shape(gf['geometry'])).symmetric_difference(pointset).area<1e-5
N={'g':'http://www.opengis.net/kml/2.2'}
km=ET.parse(D/'BNBU_v76_ACTIVE.kml').findall('.//g:Placemark',N)
assert len(km)==566 and sum(x.find('g:name',N).text==name for x in km)==1
assert not any(('GLAZING_BELT_' in n or 'LINK_GLASS_BALUSTRADE_PROPOSED' in n or 'ROOF_HOUSE_PROXY' in n) for n in b)
report={'pass':True,'version':'v76','complete_meshes':len(b),'parent_meshes_vertex_face_transform_colors_exact':len(a),
 'new_mesh_count':len(b-a),'new_mesh_triangles':len(m.faces),'watertight':True,'consistent_normals':True,
 'transparent_PBR_material_alpha_mode':m.visual.material.alphaMode,'rooftop_original_hole_retained':True,
 'new_skylight_boundary_matches_existing_rim_model_m2':float(err),
 'model_glass_surface_area_m2_not_measured':float(m.area/2),'gis_polygon_matches_GLBrim':True,
 'gpkg_layers':len(layers),'active_geojson_features':len(gis['features']),'kml_placemarks':len(km),
 'forbidden_690_faux_glazing_6_rails_5_roofrooms_not_reintroduced':True,
 'is_surveyed':False,'birdstrike_area_eligible':False,
 'remaining_hard_gaps':['official orthophoto registration','camera poses','groundway OSM nodes','DEM vertical','roof glass physical dimensions']}
(Q/'v76_independent_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print(json.dumps(report,indent=2,ensure_ascii=False))