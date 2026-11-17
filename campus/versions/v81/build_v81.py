#!/usr/bin/env python3
"""BNBU v81: evidence-gated source-preserving V60 support / V54 landing quarantine.
Parent v80 is retained byte-for-byte in input. No guessed coordinates or new objects.
"""
from pathlib import Path
import base64, hashlib, json, re, shutil
import numpy as np, trimesh, fiona
import xml.etree.ElementTree as ET
from shapely.geometry import shape, mapping, MultiPolygon
from fiona.crs import CRS
R=Path(__file__).resolve().parents[1]
I=R/'input';M=R/'model';D=R/'data';V=R/'viewer';Q=R/'qa'
for p in [M,D,V,Q]:p.mkdir(parents=True,exist_ok=True)
BASE='BNBU_v80'
SRC_GL=I/'BNBU_v80_FULL_EDITABLE.glb';SRC_GP=I/'BNBU_v80_EDITABLE_GIS.gpkg';SRC_JS=I/'BNBU_v80_ACTIVE.geojson';SRC_KML=I/'BNBU_v80_ACTIVE.kml';SRC_HTML=I/'BNBU_Campus_3D_Offline_v80.html'
photo='https://co.bnbu.edu.cn/en/images/banner2.jpg'
mapurl='https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg'
bridge='V54_LAKE00_EAST_WATER_CROSSING_SHORE_RAMP_INFERRED_ENDPOINT_MATCH'
s=trimesh.load(SRC_GL,force='scene',process=False);nodes=list(s.graph.nodes_geometry)
SUPPORT=[n for n in nodes if n.startswith('V60_P1_EASTLAKE_BOARDWALK_PAIRED_PIER_') or n.startswith('V60_P1_EASTLAKE_BOARDWALK_OPAQUE_UNDERDECK_CROSSBEAM_')]
ARCH=set(SUPPORT+[bridge]);assert len(SUPPORT)==26 and len(ARCH)==27 and len(nodes)==1374 and ARCH<=set(nodes)
assert 'V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE' in nodes
main=trimesh.Scene(); display=trimesh.Scene();metrics=[]
for n in nodes:
 t,k=s.graph[n];m=s.geometry[k].copy()
 if n in ARCH:
  display.add_geometry(m,node_name=n,geom_name=n,transform=t)
  v=trimesh.transform_points(m.vertices,t)
  metrics.append({'model_node':n,'triangles':int(len(m.faces)),'vertices':int(len(m.vertices)),
  'min_xyz':np.round(v.min(axis=0),6).tolist(),'max_xyz':np.round(v.max(axis=0),6).tolist(),
  'certainty':'type/photo supported only' if n!=bridge else 'landing location inferred',
  'status':'DISPLAY_ONLY_UNVERIFIED_NOT_ROUTABLE'})
 else:main.add_geometry(m,node_name=n,geom_name=n,transform=t)
assert len(main.graph.nodes_geometry)==1347 and len(display.graph.nodes_geometry)==27
newgl=M/'BNBU_v81_FULL_EDITABLE.glb';archivegl=M/'BNBU_v81_UNVERIFIED_PIER_STATIONS_AND_RAMP_DISPLAY_ONLY.glb'
newgl.write_bytes(main.export('glb'));archivegl.write_bytes(display.export('glb'))
# Active feature, KML and GPKG are source-identical except for evidence-layer identity.
j=json.loads(SRC_JS.read_text('utf8')); old_n=len(j['features']);accepted=[];arch_features=[]
for f in j['features']:
 if f['properties'].get('model_node') in ARCH:
  f=json.loads(json.dumps(f));f['properties'].update({'model_state':'DISPLAY_ONLY_UNSURVEYED','is_routable':0,'is_surveyed':0,
   'metric_birdstrike_eligible':0,'evidence_for_presence':photo,
   'evidence_for_exact_count_or_position':'NONE; numerical support spacing is v60 model parameter'})
  arch_features.append(f)
 else:accepted.append(f)
assert old_n==561 and len(accepted)==534 and len(arch_features)==27
j['features']=accepted;j['name']='BNBU v81 evidence-gated campus: deck retained, unmeasured 13 pier stations and endpoint ramp display-only'
(D/'BNBU_v81_ACTIVE.geojson').write_text(json.dumps(j,ensure_ascii=False,indent=1),'utf8')
(D/'BNBU_v81_DISPLAY_ONLY.geojson').write_text(json.dumps({'type':'FeatureCollection','name':'Unverified 26 boardwalk supports and one ramp; not navigable','features':arch_features},ensure_ascii=False,indent=1),'utf8')
ns='http://www.opengis.net/kml/2.2';tag=lambda q:f'{{{ns}}}{q}';ET.register_namespace('',ns)
tree=ET.parse(SRC_KML);doc=tree.getroot().find(tag('Document'))
newtree=ET.Element(tag('kml'));archive_doc=ET.SubElement(newtree,tag('Document'));archive_names=[]
for pm in list(doc.findall(tag('Placemark'))):
 name=pm.find(tag('name'))
 if name is not None and name.text in ARCH:
  doc.remove(pm); archive_doc.append(pm); archive_names.append(name.text)
assert len(archive_names)==27 and len(doc.findall(tag('Placemark')))==534
ET.ElementTree(newtree).write(D/'BNBU_v81_DISPLAY_ONLY.kml',encoding='utf8',xml_declaration=True)
tree.write(D/'BNBU_v81_ACTIVE.kml',encoding='utf8',xml_declaration=True)
# GPKG: one original v60 layer split into accepted boardwalk deck and archived supports.
gp=D/'BNBU_v81_EDITABLE_GIS.gpkg';shutil.copy2(SRC_GP,gp)
layer='v60_P1_EASTLAKE_BOARDWALK_3D_STRUCTURAL_MODEL_NOT_SURVEYED'
with fiona.open(gp,layer=layer) as src:
 fp=[{'geometry':mapping(shape(f['geometry'])),'properties':dict(f['properties'])} for f in src]
 sch=dict(src.schema['properties']);crs=src.crs
assert len(fp)==27 and {f['properties']['model_node'] for f in fp}==set(SUPPORT+['V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE'])
fiona.remove(gp,layer=layer,driver='GPKG')
sch.update({'model_state':'str','is_surveyed':'int','is_routable':'int','verified_support_count':'int','evidence_note':'str'})
for lname, subset,state in [
 ('v81_ACTIVE_V60_PHOTO_SUPPORTED_BOARDWALK_DECK', [f for f in fp if f['properties']['model_node'] not in ARCH], 'ACTIVE_MODEL_DERIVED_DECK'),
 ('v81_DISPLAY_ONLY_V60_26_UNSURVEYED_SUPPORTS',[f for f in fp if f['properties']['model_node'] in ARCH], 'DISPLAY_ONLY_NO_SUPPORT_COUNT_SURVEY')]:
 with fiona.open(gp,'w',driver='GPKG',layer=lname,schema={'geometry':'MultiPolygon','properties':sch},crs=CRS.from_epsg(4326)) as dst:
  for f in subset:
   p=dict(f['properties']);p.update({'model_state':state,'is_surveyed':0,'is_routable':0,
     'verified_support_count':0,'evidence_note':'No calibrated support count/spacing; deck location inherited and unsurveyed'})
   g=shape(f['geometry']);g=MultiPolygon([g]) if g.geom_type=='Polygon' else g
   dst.write({'geometry':mapping(g),'properties':p})
# Separately move one V54 inferred bridge landing to display-only.
oldlayer='v54_ACTIVE_EASTLAKE_BRIDGE_LANDING'
with fiona.open(gp,layer=oldlayer) as src:
 ff=[{'geometry':mapping(shape(f['geometry'])),'properties':dict(f['properties'])} for f in src];sche=dict(src.schema['properties'])
assert len(ff)==1 and ff[0]['properties']['model_node']==bridge
fiona.remove(gp,layer=oldlayer,driver='GPKG')
sche.update({'model_state':'str','is_routable':'int','is_surveyed':'int','evidence_note':'str'})
with fiona.open(gp,'w',driver='GPKG',layer='v81_DISPLAY_ONLY_V54_INFERRED_EASTLAKE_LANDING',schema={'geometry':'MultiPolygon','properties':sche},crs=CRS.from_epsg(4326)) as dst:
 for f in ff:
  p=dict(f['properties']);p.update({'model_state':'DISPLAY_ONLY_INFERRED_LANDING','is_routable':0,'is_surveyed':0,'evidence_note':'Location/grade not verified by multi-view photo or OSM way'})
  g=shape(f['geometry']); g=MultiPolygon([g]) if g.geom_type=='Polygon' else g
  dst.write({'geometry':mapping(g),'properties':p})
assert len(fiona.listlayers(gp))==146
# Standalone full viewer: replace exact original embedded parent GLB and GIS, correcting visible version tags.
h=SRC_HTML.read_text('utf8');pat=r'(<script id="embedded-v71" type="application/octet-stream">)([^<]*)(</script>)'
m=re.search(pat,h);assert m and hashlib.sha256(base64.b64decode(m.group(2))).digest()==hashlib.sha256(SRC_GL.read_bytes()).digest()
h,n=re.subn(pat,lambda q:q.group(1)+base64.b64encode(newgl.read_bytes()).decode('ascii')+q.group(3),h,count=1);assert n==1
geopat=r'(<script id="embedded-gis" type="application/json">)([^<]*)(</script>)'
h,n=re.subn(geopat,lambda q:q.group(1)+json.dumps(j,ensure_ascii=False,separators=(',',':')).replace('<',r'\u003c')+q.group(3),h,count=1);assert n==1
h=h.replace('BNBU 校园 v80','BNBU 校园 v81').replace('v80 | 6 条 V49','v81 | v80 已隔离 6 条 V49')
h=h.replace('window.__BNBU_VERSION__="v78-main-reconciled"','window.__BNBU_VERSION__="v81-evidence-gated"')
info='<aside id="v81-evidence-gate" style="color:#ffe1ab;background:#27394b;padding:7px 12px;font-size:12px">v81: V60 木栈道主桥面仍在主 GLB；13 组未经实测的桥墩/横梁（26个网格）及 V54 推定岸坡连接已转至单独 display-only GLB。本版不用于步行导航或桥柱数量测绘。</aside>'
h=h.replace('<body>','<body>'+info,1)
(V/'BNBU_Campus_3D_Offline_v81.html').write_text(h,'utf8')
record={'version':'v81','parent':'v80','original_meshes':len(nodes),'primary_meshes':len(main.graph.nodes_geometry),
 'quarantined_meshes':len(display.graph.nodes_geometry),'v60_piers':13,'v60_crossbeams':13,'v54_inferred_ramps':1,
 'quarantined_triangles':sum(x['triangles'] for x in metrics),
 'v60_boardwalk_deck_retained':True,'v76_lrc_skylight_retained':True,
 'active_geojson_features':len(accepted),'archived_geojson_features':len(arch_features),
 'gpkg_layers':len(fiona.listlayers(gp)),'source_map':mapurl,'source_photo':photo,
 'source_limitation':'photo confirms deck and support type, not number, coordinates, spacing or landing elevation',
 'GLB_frame':'EPSG:32649 local XY = UTM minus (758940,2474080), Z model relative',
 'GIS_frame':'EPSG:4326, inherited coordinates NOT survey',
 'new_surveyed_geometry':0,'new_glass_or_random_tree':0,
 'source_model_sha256':hashlib.sha256(SRC_GL.read_bytes()).hexdigest(),
 'main_model_sha256':hashlib.sha256(newgl.read_bytes()).hexdigest(),
 'quarantined_nodes':metrics}
(Q/'v81_geometry_change.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in record.items() if k!='quarantined_nodes'},ensure_ascii=False,indent=2))