#!/usr/bin/env python3
"""BNBU v80: quarantine unsupported V49 inferred paths from accepted geometry.

Requires v79 exports and bundled v78 offline HTML. Absolutely no XY/Z generation:
6 previously inferred path meshes are removed from the main GLB, retained
byte/geometrically identical in an opt-in display-only GLB, and segregated
from active GIS feature/placemark sets. All 1374 other meshes are untouched.
"""
from pathlib import Path
import base64, hashlib, json, shutil, zipfile, re
import xml.etree.ElementTree as ET
import numpy as np, trimesh, fiona
from shapely.geometry import shape,mapping,MultiPolygon
from fiona.crs import CRS
ROOT=Path(__file__).resolve().parent
IN=ROOT/'input';O=ROOT/'model';D=ROOT/'data';V=ROOT/'viewer';Q=ROOT/'qa'
for d in [O,D,V,Q]: d.mkdir(exist_ok=True)
GLB=IN/'BNBU_v79_FULL_EDITABLE.glb'
GPKG=IN/'BNBU_v79_EDITABLE_GIS.gpkg'
J=IN/'BNBU_v79_ACTIVE.geojson'
KML=IN/'BNBU_v79_ACTIVE.kml'
H=IN/'BNBU_Campus_3D_Offline_v78.html'
PFX='V49_PHASEII_D'
TARGET=tuple(f'{PFX}{i}_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE' for i in range(1,7))
SRC='https://www.bnbu.edu.cn/info/1078/13974.htm'
MAP='https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg'
source=trimesh.load(GLB,force='scene',process=False)
names=list(source.graph.nodes_geometry)
assert len(names)==1380 and set(TARGET).issubset(names)
main=trimesh.Scene();arch=trimesh.Scene();metrics=[]
for name in names:
 transform,key=source.graph[name];m=source.geometry[key].copy()
 if name in TARGET:
  arch.add_geometry(m,node_name=name,geom_name=name,transform=transform)
  vv=trimesh.transform_points(m.vertices,transform)
  metrics.append({'name':name,'vertices':int(len(vv)),'triangles':int(len(m.faces)),
   'model_xyz_min':np.round(vv.min(axis=0),6).tolist(),'model_xyz_max':np.round(vv.max(axis=0),6).tolist(),
   'watertight':bool(m.is_watertight),'source':'v49 inherited, path alignment unverified',
   'display_only':True,'is_routable':False,'is_surveyed':False})
 else:main.add_geometry(m,node_name=name,geom_name=name,transform=transform)
assert len(main.graph.nodes_geometry)==1374 and len(arch.graph.nodes_geometry)==6
MAIN=O/'BNBU_v80_ACCEPTED_NO_INFERRED_LINKS.glb';ARCH=O/'BNBU_v80_V49_UNVERIFIED_LINKS_DISPLAY_ONLY.glb'
MAIN.write_bytes(main.export('glb'));ARCH.write_bytes(arch.export('glb'))
# GeoPackage: archive the single previously 'ACTIVE' layer under a clearly opt-in name.
shutil.copy2(GPKG,D/'BNBU_v80_EDITABLE_GIS.gpkg');out_gpkg=D/'BNBU_v80_EDITABLE_GIS.gpkg'
old_layer='v49_ACTIVE_P2_GRADE_MATCH_GROUND_PATHS'; archive_layer='v80_DISPLAY_ONLY_V49_UNVERIFIED_PATHS_NOT_ROUTABLE'
with fiona.open(GPKG,layer=old_layer) as src:
 features=[{'geometry':dict(x['geometry']),'properties':dict(x['properties'])} for x in src];crs=src.crs
assert len(features)==6 and {x['properties']['model_node'] for x in features}==set(TARGET)
fiona.remove(out_gpkg,layer=old_layer,driver='GPKG')
props_schema=dict(fiona.open(GPKG,layer=old_layer).schema['properties'])
props_schema.update({'model_state':'str','is_routable':'int','is_surveyed':'int','quarantine_reason':'str','evidence_url':'str'})
with fiona.open(out_gpkg,'w',driver='GPKG',layer=archive_layer,
 schema={'geometry':'MultiPolygon','properties':props_schema},crs=CRS.from_epsg(4326)) as dst:
 for f in features:
  p=dict(f['properties']);p.update({'model_state':'DISPLAY_ONLY_UNVERIFIED','is_routable':0,'is_surveyed':0,
  'quarantine_reason':'No photographed/mapped centerline or surveyed connection; do not infer pathway',
  'evidence_url':SRC}); gg=shape(f['geometry']); gg=MultiPolygon([gg]) if gg.geom_type=='Polygon' else gg;dst.write({'geometry':mapping(gg),'properties':p})
# Active GeoJSON explicitly excludes quarantined polygons (they remain in an archive file).
j=json.loads(J.read_text('utf8')); assert len(j['features'])==567
keep=[];split=[]
for f in j['features']:
 if f['properties'].get('model_node') in TARGET:
  f=dict(f);f['properties']=dict(f['properties']);f['properties'].update({'model_state':'DISPLAY_ONLY_UNVERIFIED','is_routable':0,'is_surveyed':0,'is_active':0,'source_evidence':SRC});split.append(f)
 else:keep.append(f)
assert len(split)==6 and len(keep)==561
j['features']=keep;j['name']='BNBU v80 accepted inherited geometry EXCLUDING unverified V49 center paths; not surveyed'
(D/'BNBU_v80_ACTIVE.geojson').write_text(json.dumps(j,ensure_ascii=False,indent=1),'utf8')
(D/'BNBU_v80_UNVERIFIED_LINKS_DISPLAY_ONLY.geojson').write_text(json.dumps({'type':'FeatureCollection','name':'V49 unverified candidate paths (DISPLAY ONLY; not routes)','features':split},ensure_ascii=False,indent=1),'utf8')
# KML: preserve 561 and segregate six exact placemarks, not merely relabel them.
ns='http://www.opengis.net/kml/2.2';t=lambda k:f'{{{ns}}}{k}';ET.register_namespace('',ns)
tree=ET.parse(KML);doc=tree.getroot().find(t('Document'));oldmarks=doc.findall(t('Placemark'))
assert len(oldmarks)==567
separate=ET.Element(t('kml'));d2=ET.SubElement(separate,t('Document'));found=[]
for p in oldmarks:
 n=p.find(t('name'))
 if n is not None and n.text in TARGET:
  doc.remove(p);d2.append(p);found.append(n.text)
assert len(found)==6 and len(doc.findall(t('Placemark')))==561
ET.ElementTree(separate).write(D/'BNBU_v80_UNVERIFIED_LINKS_DISPLAY_ONLY.kml',encoding='utf8',xml_declaration=True)
tree.write(D/'BNBU_v80_ACTIVE.kml',encoding='utf8',xml_declaration=True)
# Reuse fully offline 3D viewer, replacing only embedded parent GLB (no fetch, no CDN).
s=H.read_text('utf8')
pattern=r'(<script id="embedded-v71" type="application/octet-stream">)([^<]*)(</script>)'
original=re.search(pattern,s)
assert original
embedded_parent=base64.b64decode(original.group(2))
assert hashlib.sha256(embedded_parent).hexdigest()==hashlib.sha256(GLB.read_bytes()).hexdigest(), 'viewer and source model must be byte-identical before replacement'
viewer_payload=base64.b64encode(MAIN.read_bytes()).decode('ascii')
s,n=re.subn(pattern,lambda m:m.group(1)+viewer_payload+m.group(3),s,count=1)
assert n==1
s=s.replace('BNBU 校园 v78', 'BNBU 校园 v80',2)
s=s.replace('v78 · 已验证主场景', 'v80 · 主场景排除六处未经证实的 V49 连路',1)
# In-text status banner added; never claims public Pages availability.
status='''<aside id="v80-provenance-status" role="status" style="padding:8px 12px;background:#273548;color:#f7df9a;font-size:12px;border-bottom:1px solid #685c3e">
 v80 | 6 条 V49 无实测路径已从主 GLB 移至可选、非导航的独立候选 GLB。二期 D1–D6 道路和宿舍入口尚未通过 OSM/正射配准；不能按显示的模型连通性导航。支持查看后退回 v79 对照文件。
 </aside>'''
s=s.replace('<body>', '<body>\n'+status,1)
# Replace outdated embedded GIS with precisely the same 561 accepted features.
geo_pat=r'(<script id="embedded-gis" type="application/json">)([^<]*)(</script>)'
assert re.search(geo_pat,s)
s,gn=re.subn(geo_pat,lambda m:m.group(1)+json.dumps(j,ensure_ascii=False,separators=(',',':')).replace('<',r'\u003c')+m.group(3),s,count=1)
assert gn==1
viewer_path=V/'BNBU_Campus_3D_Offline_v80.html';viewer_path.write_text(s,'utf8')
# Source evidence / opt-in external artifact manifest. The HTML renders only accepted meshes.
manifest={'version':'v80','parent':'v79','change':'quarantine six non-surveyed V49 radial-to-court inferred connectors',
 'main_n':1374,'parent_n':1380,'display_only_n':6,'unchanged_node_n':1374,
 'removed_names':list(TARGET),'archive_names':found,'removed_triangles':sum(m['triangles'] for m in metrics),
 'parent_sha256':hashlib.sha256(GLB.read_bytes()).hexdigest(),'main_sha256':hashlib.sha256(MAIN.read_bytes()).hexdigest(),
 'archive_sha256':hashlib.sha256(ARCH.read_bytes()).hexdigest(),
 'official_map':MAP,'photo_phaseII_construction':SRC,'surveyed_ground_connections':0,
 'new_approved_routes':0,'new_windows_glass_tree_roofrooms':0,
 'GIS_crs':'EPSG:4326','GLB_crs':'EPSG:32649 XY minus 758940,2474080; Z relative',
 'active_geojson_count':len(keep),'display_only_geojson_count':len(split),
 'gpkg_layers':len(fiona.listlayers(out_gpkg)),'v49_legacy_layer_removed':old_layer not in fiona.listlayers(out_gpkg),
 'v80_archive_layer_present':archive_layer in fiona.listlayers(out_gpkg),
 'photographic_reconstruction':'Not performed; 2022 aerial shows radial topology, does not survey individual centerlines',
 'github_pages':'Not verified as live; offline viewer is self-contained', 'components':metrics}
(Q/'v80_geometry_change.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in manifest.items() if k not in ['components','removed_names','archive_names']},ensure_ascii=False,indent=2))