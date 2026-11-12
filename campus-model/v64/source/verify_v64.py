#!/usr/bin/env python3
"""Independently re-open edited GLB and validate all geometry, GIS, provenance."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
import numpy as np, trimesh, fiona
from shapely.geometry import shape
R=Path(__file__).resolve().parents[1];I=R/'input';M=R/'model';D=R/'data';Q=R/'qa'
a=trimesh.load(I/'BNBU_v63_FULL_EDITABLE.glb',force='scene',process=False)
b=trimesh.load(M/'BNBU_v64_FULL_EDITABLE.glb',force='scene',process=False)
d=json.loads((Q/'v64_build.json').read_text('utf8'))
assert len(a.graph.nodes_geometry)==len(b.graph.nodes_geometry)==1381
mods=d['actually_modified_hill_meshes'];prior={x['parent_node'] for x in mods};now={x['model_node'] for x in mods}
assert len(mods)==len(prior)==len(now)==4
A=set(a.graph.nodes_geometry);B=set(b.graph.nodes_geometry)
assert A-B==prior and B-A==now and len(A&B)==1377
for name in A&B:
 t,k=a.graph[name];u,l=b.graph[name]
 assert np.array_equal(t,u),name
 am=a.geometry[k];bm=b.geometry[l]
 assert np.array_equal(am.vertices,bm.vertices),name
 assert np.array_equal(am.faces,bm.faces),name
 if hasattr(am.visual,"vertex_colors") and hasattr(bm.visual,"vertex_colors"):
  assert np.array_equal(am.visual.vertex_colors,bm.visual.vertex_colors),name
 elif hasattr(am.visual,"uv") and hasattr(bm.visual,"uv"):
  assert np.array_equal(am.visual.uv,bm.visual.uv),name
assert all(not any(p in n for p in ('GLAZING_BELT_','LINK_GLASS_BALUSTRADE_PROPOSED','ROOF_HOUSE_PROXY')) for n in B)
err=[];shift=[];tri=0;new_volume=[]
for x in mods:
 ta,ka=a.graph[x['parent_node']];tb,kb=b.graph[x['model_node']]
 assert np.array_equal(ta,tb)
 old=a.geometry[ka];new=b.geometry[kb]
 assert old.is_watertight and new.is_watertight and new.is_winding_consistent and new.volume>0
 assert np.array_equal(old.faces,new.faces)
 assert np.array_equal(old.vertices[:,:2],new.vertices[:,:2])
 assert np.array_equal(old.visual.vertex_colors,new.visual.vertex_colors)
 delta=np.abs(old.vertices[:,2]-new.vertices[:,2]);shift.append(float(delta.max()))
 assert delta.max()<=.350003
 assert np.count_nonzero(delta>1.e-6)==x['edited_vertices']
 assert np.isclose(old.vertices[:,2].max(),new.vertices[:,2].max())
 assert np.isclose(old.vertices[:,2].min(),new.vertices[:,2].min())
 tri+=len(new.faces);new_volume.append(new.volume)
 assert abs(new.volume-old.volume)/old.volume<.03
assert len(fiona.listlayers(D/'BNBU_v64_EDITABLE_GIS.gpkg'))==141
prev=json.loads((I/'BNBU_v63_ACTIVE.geojson').read_text('utf8'));js=json.loads((D/'BNBU_v64_ACTIVE.geojson').read_text('utf8'))
assert len(prev['features'])==527 and len(js['features'])==531
assert prev['features']==js['features'][:527]
orig={f['properties'].get('model_node'):f for f in prev['features']}
newf={f['properties'].get('model_node'):f for f in js['features'][527:]}
assert set(newf)==now
with fiona.open(D/'BNBU_v64_EDITABLE_GIS.gpkg',layer='v64_four_actual_3D_hill_slope_refinements_not_DEM') as src:
 assert len(src)==4 and src.crs.to_epsg()==4326
 for r in src:
  n=r['properties']['model_node'];p=newf[n]['properties']['parent_node']
  assert shape(r['geometry']).equals_exact(shape(orig[p]['geometry']),tolerance=1e-9)
  assert r['properties']['is_surveyed']==0 and r['properties']['is_dem']==0
for f in js['features'][527:]:
 assert f['properties']['is_glass']==0 and f['properties']['metric_birdstrike_eligible']==0
ns={'k':'http://www.opengis.net/kml/2.2'}
kml=ET.parse(D/'BNBU_v64_ACTIVE.kml');places=kml.findall('.//k:Placemark',ns)
assert len(places)==531
qa={'version':'v64','pass':True,'full_reimport_mesh_count':len(B),'exactly_retained_original_meshes':len(A&B),
 'source_terrain_meshes_replaced':len(prior),'all_modified_watertight_and_winding':True,
 'changed_terrain_triangle_count':tri,'max_abs_vertex_z_shift':max(shift),
 'maximum_original_xy_error':0.0,'parent_summits_and_terrain_xy_retained':True,
 'parent_v63_GIS_features_unchanged':527,'GPKG_layers':141,'GeoJSON_features':531,'KML_placemarks':531,
 'prohibited_glazing_still_absent':True,'DEM_attested':False,'real_OSM_way_vertices_added':0,
 'warning':'Smoothing corrects visual/high-frequency facets only; no elevation survey, no independent photo registration.'}
(Q/'v64_independent_validation.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(qa,indent=2))