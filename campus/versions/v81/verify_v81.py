#!/usr/bin/env python3
"""Independent re-import of v81 model + GIS against exact v80 source assets."""
from pathlib import Path
import json,base64,re,hashlib,xml.etree.ElementTree as ET
import numpy as np, trimesh, fiona
from shapely.geometry import shape
R=Path(__file__).resolve().parents[1];I=R/'input';M=R/'model';D=R/'data';V=R/'viewer';Q=R/'qa'
src=trimesh.load(I/'BNBU_v80_FULL_EDITABLE.glb',force='scene',process=False)
new=trimesh.load(M/'BNBU_v81_FULL_EDITABLE.glb',force='scene',process=False)
arch=trimesh.load(M/'BNBU_v81_UNVERIFIED_PIER_STATIONS_AND_RAMP_DISPLAY_ONLY.glb',force='scene',process=False)
a=set(src.graph.nodes_geometry);b=set(new.graph.nodes_geometry);c=set(arch.graph.nodes_geometry)
assert b.isdisjoint(c) and a==b|c and len((a,b,c))==3
assert len(a)==1374 and len(b)==1347 and len(c)==27
assert 'V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED' in b
assert 'V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE' in b
assert not any('GLAZING_BELT_' in n or 'LINK_GLASS_BALUSTRADE_PROPOSED' in n or 'ROOF_HOUSE_PROXY' in n for n in b)
faces=0
for n in a:
 original=src;target=new if n in b else arch
 x,k=original.graph[n];y,j=target.graph[n];u=original.geometry[k];v=target.geometry[j]
 assert np.array_equal(x,y) and np.array_equal(u.vertices,v.vertices) and np.array_equal(u.faces,v.faces),n
 if hasattr(u.visual,'vertex_colors') and hasattr(v.visual,'vertex_colors'):
  assert np.array_equal(u.visual.vertex_colors,v.visual.vertex_colors),n
 else:
  assert u.visual.kind==v.visual.kind,n
 if n in c:faces+=len(u.faces)
assert faces==2476
geo=json.loads((D/'BNBU_v81_ACTIVE.geojson').read_text('utf8'))
ar_geo=json.loads((D/'BNBU_v81_DISPLAY_ONLY.geojson').read_text('utf8'))
source_geo=json.loads((I/'BNBU_v80_ACTIVE.geojson').read_text('utf8'))
assert len(geo['features'])==534 and len(ar_geo['features'])==27
assert {f['properties'].get('model_node') for f in ar_geo['features']}==c
assert {f['properties'].get('model_node') for f in geo['features']}.isdisjoint(c)
by_original={f['properties'].get('model_node'):shape(f['geometry']) for f in source_geo['features']}
for f in ar_geo['features']:
 name=f['properties']['model_node']
 assert f['properties']['is_surveyed']==0 and f['properties']['is_routable']==0
 assert shape(f['geometry']).equals_exact(by_original[name],tolerance=1.e-8)
ns={'k':'http://www.opengis.net/kml/2.2'}
active_placemarks=ET.parse(D/'BNBU_v81_ACTIVE.kml').findall('.//k:Placemark',ns)
archive_placemarks=ET.parse(D/'BNBU_v81_DISPLAY_ONLY.kml').findall('.//k:Placemark',ns)
assert len(active_placemarks)==534 and len(archive_placemarks)==27
assert {n.find('k:name',ns).text for n in archive_placemarks}==c
layers=fiona.listlayers(D/'BNBU_v81_EDITABLE_GIS.gpkg')
assert len(layers)==146
assert all(x in layers for x in ['v81_ACTIVE_V60_PHOTO_SUPPORTED_BOARDWALK_DECK','v81_DISPLAY_ONLY_V60_26_UNSURVEYED_SUPPORTS','v81_DISPLAY_ONLY_V54_INFERRED_EASTLAKE_LANDING'])
for x,expected in [('v81_ACTIVE_V60_PHOTO_SUPPORTED_BOARDWALK_DECK',1),('v81_DISPLAY_ONLY_V60_26_UNSURVEYED_SUPPORTS',26),('v81_DISPLAY_ONLY_V54_INFERRED_EASTLAKE_LANDING',1)]:
 with fiona.open(D/'BNBU_v81_EDITABLE_GIS.gpkg',layer=x) as collection:
  assert len(collection)==expected and collection.crs.to_epsg()==4326
  for f in collection: assert f['properties']['is_routable']==0
h=(V/'BNBU_Campus_3D_Offline_v81.html').read_text('utf8')
mg=re.search(r'<script id="embedded-v71" type="application/octet-stream">([^<]+)</script>',h)
assert mg and hashlib.sha256(base64.b64decode(mg.group(1))).digest()==hashlib.sha256((M/'BNBU_v81_FULL_EDITABLE.glb').read_bytes()).digest()
assert 'window.__BNBU_VERSION__="v81-evidence-gated"' in h
assert 'v81-evidence-gate' in h
jg=re.search(r'<script id="embedded-gis" type="application/json">([^<]+)</script>',h)
assert jg and len(json.loads(jg.group(1))['features'])==534
report={'pass':True,'version':'v81','parent_mesh_count':1374,'active_mesh_count':len(b),'display_only_mesh_count':len(c),'display_only_triangles':faces,
'parent_unmodified_meshes':len(b),'archived_exactly':len(c),'active_deck_kept':True,'lrc_skylight_kept':True,'geojson':534,'display_only_geojson':27,'kml_active':534,'gpkg_layers':146,
'primary_glb_sha256':hashlib.sha256((M/'BNBU_v81_FULL_EDITABLE.glb').read_bytes()).hexdigest(),
'full_webgl_browser_verified':False,'coordinate_precision':'inherited proxy XY, non-surveyed model relative Z',
'error_budget':'No new ground truth; no physical river crossings inferred'}
(Q/'v81_independent_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,indent=2,ensure_ascii=False))