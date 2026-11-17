#!/usr/bin/env python3
"""Independent verification for v80 selective quarantine; no reliance on builder state."""
from pathlib import Path
import hashlib,json,re,base64,xml.etree.ElementTree as ET,collections
import numpy as np,trimesh,fiona
from shapely.geometry import shape
R=Path(__file__).resolve().parent; I=R/'input';O=R/'model';D=R/'data';V=R/'viewer';Q=R/'qa'
old=trimesh.load(I/'BNBU_v79_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(O/'BNBU_v80_ACCEPTED_NO_INFERRED_LINKS.glb',force='scene',process=False)
arch=trimesh.load(O/'BNBU_v80_V49_UNVERIFIED_LINKS_DISPLAY_ONLY.glb',force='scene',process=False)
old_names=set(old.graph.nodes_geometry);new_names=set(new.graph.nodes_geometry);arch_names=set(arch.graph.nodes_geometry)
assert len(old_names)==1380 and len(new_names)==1374 and len(arch_names)==6
assert new_names.isdisjoint(arch_names) and old_names==new_names|arch_names
assert all(n.startswith('V49_PHASEII_D') and n.endswith('GROUND_LINK_INFERRED_NOT_BRIDGE') for n in arch_names)

def same(n,s1,s2):
 t1,k1=s1.graph[n];t2,k2=s2.graph[n];a=s1.geometry[k1];b=s2.geometry[k2]
 assert np.array_equal(t1,t2), n
 assert np.array_equal(a.vertices,b.vertices),n
 assert np.array_equal(a.faces,b.faces),n
 assert type(a.visual)==type(b.visual),n
 if hasattr(a.visual,'vertex_colors'):assert np.array_equal(a.visual.vertex_colors,b.visual.vertex_colors),n
 if hasattr(a.visual,'material') and hasattr(b.visual,'material'):
  assert a.visual.material.name==b.visual.material.name,n
for n in new_names:same(n,old,new)
for n in arch_names:same(n,old,arch)
# Confirm v76 reconciled LRC skylight geometry is preserved, not replaced by a coincidental same-name mesh.
v76=trimesh.load('/mnt/data/BNBU_v76_FULL_EDITABLE.glb',force='scene',process=False)
skylight=[n for n in old_names if n.startswith('V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS')]
assert len(skylight)==1 and skylight[0] in v76.graph.nodes_geometry
same(skylight[0],v76,new)
# Any previously excluded speculative panes/penthouses remain absent.
for n in new_names:
 assert not any(x in n for x in ['GLAZING_BELT_', 'ROOF_HOUSE_PROXY','LINK_GLASS_BALUSTRADE_PROPOSED']),n
parent_geo=json.loads((I/'BNBU_v79_ACTIVE.geojson').read_text('utf8'))
active_geo=json.loads((D/'BNBU_v80_ACTIVE.geojson').read_text('utf8'))
arch_geo=json.loads((D/'BNBU_v80_UNVERIFIED_LINKS_DISPLAY_ONLY.geojson').read_text('utf8'))
prefix='V49_PHASEII_D'
pa=parent_geo['features'];aa=active_geo['features'];bb=arch_geo['features']
assert len(pa)==567 and len(aa)==561 and len(bb)==6
original_kept=[f for f in pa if f['properties'].get('model_node') not in arch_names]
assert original_kept==aa
original_arch={f['properties']['model_node']:f for f in pa if f['properties'].get('model_node') in arch_names}
f2={f['properties']['model_node']:f for f in bb}
assert set(f2)==arch_names and set(original_arch)==arch_names
for n in f2:
 assert shape(original_arch[n]['geometry']).equals_exact(shape(f2[n]['geometry']),0)
 assert f2[n]['properties']['is_routable']==0
old_gpkg=I/'BNBU_v79_EDITABLE_GIS.gpkg';new_gpkg=D/'BNBU_v80_EDITABLE_GIS.gpkg'
layers_before=fiona.listlayers(old_gpkg);layers_after=fiona.listlayers(new_gpkg)
assert len(layers_before)==len(layers_after)==145
assert set(layers_before)-set(layers_after)=={'v49_ACTIVE_P2_GRADE_MATCH_GROUND_PATHS'}
assert set(layers_after)-set(layers_before)=={'v80_DISPLAY_ONLY_V49_UNVERIFIED_PATHS_NOT_ROUTABLE'}
with fiona.open(old_gpkg,layer='v49_ACTIVE_P2_GRADE_MATCH_GROUND_PATHS') as orig, fiona.open(new_gpkg,layer='v80_DISPLAY_ONLY_V49_UNVERIFIED_PATHS_NOT_ROUTABLE') as seg:
 old_f={f['properties']['model_node']:f for f in orig};new_f={f['properties']['model_node']:f for f in seg}
 assert set(old_f)==set(new_f)==arch_names and seg.crs.to_epsg()==4326
 for n in arch_names:
  assert shape(old_f[n]['geometry']).symmetric_difference(shape(new_f[n]['geometry'])).area==0
  assert new_f[n]['properties']['model_state']=='DISPLAY_ONLY_UNVERIFIED'
  assert new_f[n]['properties']['is_routable']==0
# GPKG library retention is checked using SQLite metadata and key scientific layers.
import sqlite3
with sqlite3.connect(old_gpkg) as db1, sqlite3.connect(new_gpkg) as db2:
 oldmeta=db1.execute("SELECT table_name, data_type, srs_id FROM gpkg_contents ORDER BY table_name").fetchall()
 newmeta=db2.execute("SELECT table_name, data_type, srs_id FROM gpkg_contents ORDER BY table_name").fetchall()
 keep1=[x for x in oldmeta if x[0]!='v49_ACTIVE_P2_GRADE_MATCH_GROUND_PATHS']
 keep2=[x for x in newmeta if x[0]!='v80_DISPLAY_ONLY_V49_UNVERIFIED_PATHS_NOT_ROUTABLE']
 assert keep1==keep2
for ln in ['v76_existing_LRC_atrium_skylight_glazing_nonmetric','bnbu_v78_scene_membership','bnbu_v79_surface_layer_checks']:
 with fiona.open(old_gpkg,layer=ln) as src, fiona.open(new_gpkg,layer=ln) as dst:
  assert len(src)==len(dst)
  for i,(a,b) in enumerate(zip(src,dst)):
   assert dict(a['properties'])==dict(b['properties'])
   if a['geometry'] is not None:assert shape(a['geometry']).equals_exact(shape(b['geometry']),0)
ns={'k':'http://www.opengis.net/kml/2.2'}
def klist(path):
 rt=ET.parse(path).getroot();return [n.text for n in rt.findall('.//k:Placemark/k:name',ns)]
knames=klist(D/'BNBU_v80_ACTIVE.kml');archk=klist(D/'BNBU_v80_UNVERIFIED_LINKS_DISPLAY_ONLY.kml')
assert len(knames)==561 and len(archk)==6 and set(archk)==arch_names
assert set(knames)==set(klist(I/'BNBU_v79_ACTIVE.kml'))-arch_names
# Viewer embeds exact GLB, not parent geometry, and latest active GIS without six ghost routes.
html=(V/'BNBU_Campus_3D_Offline_v80.html').read_text('utf8')
g=re.search(r'<script id="embedded-v71" type="application/octet-stream">([^<]*)</script>',html);assert g
embedded=base64.b64decode(g.group(1)); assert hashlib.sha256(embedded).digest()==hashlib.sha256((O/'BNBU_v80_ACCEPTED_NO_INFERRED_LINKS.glb').read_bytes()).digest()
gj=re.search(r'<script id="embedded-gis" type="application/json">([^<]*)</script>',html);assert gj
assert len(json.loads(gj.group(1))['features'])==561
assert '<aside id="v80-provenance-status"' in html
assert 'https://cdn.' not in html[:100000]
report={'version':'v80','passed':True,'parent_meshes':1380,'accepted_meshes':1374,'unchanged_meshes_bitwise_arrays':1374,
 'quarantined_inferred_path_meshes':6,'quarantined_triangles':sum(len(arch.geometry[arch.graph[n][1]].faces) for n in arch_names),
 'quarantined_source_arrays_exact':True,'v76_sky_glazing_mesh_unchanged':True,
 'GPKG_layers_unchanged_count':145,'untouched_gpkg_metadata_layers_preserved':144,'detailed_gpkg_layer_checks':3,
 'old_v49_ACTIVE_layer_absent':True,'new_display_only_GPKG_layer_records':6,
 'active_geojson_features':561,'archived_geojson_features':6,'KML_active':561,'KML_archived':6,
 'viewer_embedded_glb_sha256_verified':True,'viewer_embedded_gis_current':True,
 'coordinate_crs':'EPSG:32649 with X/Y offset (758940,2474080), Z only local relative; GIS EPSG:4326',
 'new_surveyed_footpaths':0,'new_photogrammetric_coordinates':0,
 'warning':'Disabling six routes does NOT prove no footpaths; existing roads/dorm model remain unsurveyed. Browser WebGL screenshot requires separate testing.'}
(Q/'v80_independent_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))