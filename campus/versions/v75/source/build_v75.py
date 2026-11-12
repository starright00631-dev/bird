#!/usr/bin/env python3
"""Integrate geometrically safe v64/v74 work, close proven pinched opaque story trims.

NO new surveyed features. All new solids are reconstructions of inherited geometry.
Two small LRC pavement joints are imported from v71 with source provenance and
remain non-routable; four speculative CTV meshes are quarantined, not drawn.
"""
from pathlib import Path
import copy, json, shutil, xml.etree.ElementTree as ET
import numpy as np, shapely, trimesh, fiona
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union, transform as shp_transform
from pyproj import Transformer
from fiona.crs import CRS

R=Path(__file__).resolve().parents[1]; I=R/'input'; O=R/'model'; D=R/'data'; Q=R/'qa'
for p in (O,D,Q):p.mkdir(exist_ok=True,parents=True)
ORIGIN=(758940.0,2474080.0); L2G=Transformer.from_crs(32649,4326,always_xy=True)
def to_geo(g):return shp_transform(lambda x,y,z=None:L2G.transform(np.asarray(x)+ORIGIN[0],np.asarray(y)+ORIGIN[1]),g)
SCENE=trimesh.load(I/'BNBU_v64_FULL_EDITABLE.glb',force='scene',process=False)
V71=trimesh.load(I/'BNBU_v71_CONNECTED_LAKEFRONT.glb',force='scene',process=False)
assert len(SCENE.graph.nodes_geometry)==1381
old_nodes=list(SCENE.graph.nodes_geometry)
CTV_MESHES=[n for n in old_nodes if 'CTV_CC401' in n]
assert len(CTV_MESHES)==4,CTV_MESHES
CTV_GIS_NODES={
 'V53_CTV_CC401_SIDE_HOUSE_FOUNDATION_USER_REPORTED_UNSURVEYED',
 'V53_CTV_CC401_SIDE_HOUSE_WALLS_USER_REPORTED_UNSURVEYED',
 'V53_CTV_CC401_SIDE_HOUSE_SIMPLE_GABLE_ROOF_SHAPE_UNVERIFIED',
 'V53_CTV_CC401_ADJACENT_SHORT_ACCESS_SPUR_MODE_UNVERIFIED',
 'V54_CTV_CC401_HOUSE_ACCESS_JOIN_WALK040_USE_MODE_UNVERIFIED'}
assert set(CTV_MESHES).issubset(CTV_GIS_NODES)

# Source-derived watertight solids: a near-point tangent in a legacy model
# makes ring and cavity meet at one point. 0.5mm is below model's survey
# credibility and replaces that mathematical singularity (not a new window).
TOPOLOGY_CLEARANCE=0.0005

def extrude_polygon(p,z0,z1):
 ixmap={}; vertices=[]; faces=[]
 def ix(xy,z):
  k=(round(float(xy[0]),7),round(float(xy[1]),7),round(float(z),7))
  if k not in ixmap:ixmap[k]=len(vertices);vertices.append(k)
  return ixmap[k]
 for tri in shapely.constrained_delaunay_triangles(p).geoms:
  if not p.covers(tri.representative_point()):continue
  xy=np.asarray(tri.exterior.coords[:3],dtype='float64')
  cross=np.linalg.det(np.stack((xy[1]-xy[0],xy[2]-xy[0])))
  if abs(cross)<1e-12:continue
  if cross<0:xy=xy[::-1]
  faces.append([ix(v,z1) for v in xy]);faces.append([ix(v,z0) for v in xy[::-1]])
 for ring in [p.exterior,*p.interiors]:
  for a,b in zip(list(ring.coords)[:-1],list(ring.coords)[1:]):
   faces.extend([[ix(a,z0),ix(b,z0),ix(b,z1)],[ix(a,z0),ix(b,z1),ix(a,z1)]])
 m=trimesh.Trimesh(vertices=np.asarray(vertices),faces=np.asarray(faces),process=True)
 m.fix_normals()
 if m.volume<0:m.invert()
 return m

def solid(poly,z0,z1):
 a=[extrude_polygon(p,z0,z1) for p in (poly.geoms if isinstance(poly,MultiPolygon) else [poly])]
 m=trimesh.util.concatenate(a)
 assert m.is_watertight and m.is_winding_consistent and m.volume>0
 return m

replacements=[]
for name in old_nodes:
 if not name.startswith('FLOOR_EDGE_NOT_GLASS_STORYBAND_'):continue
 tf,k=SCENE.graph[name];old=SCENE.geometry[k]
 if old.is_watertight:continue
 vv=trimesh.transform_points(old.vertices,tf); tris=vv[old.faces]
 zlo,zhi=vv[:,2].min(),vv[:,2].max()
 mask=(np.ptp(tris[:,:,2],axis=1)<1e-5)&(np.abs(tris[:,:,2].mean(axis=1)-zhi)<1e-4)
 p=unary_union([Polygon(t[:,:2]) for t in tris[mask] if Polygon(t[:,:2]).area>1e-10])
 # all 37 have one intentionally pinched boundary, no valid survey resolves it
 q=p.buffer(-TOPOLOGY_CLEARANCE,join_style='mitre').buffer(TOPOLOGY_CLEARANCE,join_style='mitre')
 assert q.is_valid and q.area>0
 footprint_delta=p.symmetric_difference(q).area
 assert footprint_delta<0.0001,(name,footprint_delta)
 m=solid(q,zlo,zhi)
 orig_colors=np.unique(old.visual.vertex_colors,axis=0)
 assert len(orig_colors)==1,(name,orig_colors)
 m.visual.vertex_colors=np.tile(orig_colors[0],(len(m.vertices),1))
 newname='V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_'+name.split('STORYBAND_')[1]
 replacements.append({'old':name,'new':newname,'mesh':m,'polygon_parent':p,'polygon_new':q,'zlo':float(zlo),'zhi':float(zhi),
  'symdiff_m2':float(footprint_delta),'hausdorff_m':float(p.hausdorff_distance(q))})
assert len(replacements)==37,len(replacements)

# Geometry merge from independently checked v71 source; retain original mesh
# name, vertex colors, transform and source's inferred-not-surveyed status.
source_patch_info=json.loads((R/'reference'/'BNBU_v71_CONNECTION_PROVENANCE.json').read_text('utf8'))['source_bounded_patches']
patch_names={x['properties']['name'] for x in source_patch_info}
assert len(patch_names)==2
assert patch_names.isdisjoint(old_nodes)
new=trimesh.Scene(); quarantine=trimesh.Scene();retired=trimesh.Scene()
removed={x['old'] for x in replacements}
for name in old_nodes:
 tf,k=SCENE.graph[name]
 if name in CTV_MESHES:quarantine.add_geometry(SCENE.geometry[k].copy(),node_name=name,geom_name=name,transform=tf)
 elif name in removed:retired.add_geometry(SCENE.geometry[k].copy(),node_name=name,geom_name=name,transform=tf)
 else:new.add_geometry(SCENE.geometry[k].copy(),node_name=name,geom_name=name,transform=tf)
for x in replacements:new.add_geometry(x['mesh'],node_name=x['new'],geom_name=x['new'])
for name in sorted(patch_names):
 tf,k=V71.graph[name]; m=V71.geometry[k].copy()
 assert m.is_watertight
 # v71 imported mesh is sealed but has inconsistent triangle winding and negative signed volume.
 # Repair orientation only, without moving a single source vertex.
 m.fix_normals()
 assert m.is_watertight and m.is_winding_consistent and m.volume>0
 new.add_geometry(m,node_name=name,geom_name=name,transform=tf)
assert len(new.graph.nodes_geometry)==1381-4+2==1379
(O/'BNBU_v75_FULL_EDITABLE.glb').write_bytes(new.export('glb'))
(O/'BNBU_v75_CLOSED_STORYTRIMS_ONLY.glb').write_bytes(trimesh.Scene({x['new']:x['mesh'] for x in replacements}).export('glb'))
(O/'BNBU_v75_QUARANTINED_CTV_NOT_SURVEYED.glb').write_bytes(quarantine.export('glb'))
(O/'BNBU_v75_ARCHIVED_UNCLOSED_EDGES.glb').write_bytes(retired.export('glb'))

provenance='BNBU_v64_FULL_EDITABLE.glb inherited upper face triangulation, no field measurement'
new_f=[]
for x in replacements:
 name=x['new'];building=x['old'].split('STORYBAND_')[1].split('_')[0]
 props={'model_node':name,'parent_node':x['old'],'asset':'opaque_floor_edge','building':building,
  'source_geometry':provenance,'source_2025_map':'https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg',
  'source_type':'inherited_mesh_topology; handdrawn source only for structural context',
  'edit':'0.5 mm mathematical pinch release + re-triangulation, exact retained Z',
  'confidence_xy':'UNSURVEYED_PARENT_MODEL','confidence_z':'UNSURVEYED_PARENT_RELATIVE_Z',
  'relative_z_min':x['zlo'],'relative_z_max':x['zhi'],
  'original_top_area_model_m2':float(x['polygon_parent'].area),
  'footprint_symmetric_difference_model_m2':x['symdiff_m2'],
  'boundary_max_displacement_model_m':x['hausdorff_m'],
  'is_surveyed':0,'is_glass':0,'is_routable':0,'metric_birdstrike_eligible':0,'crs_gis':'EPSG:4326',
  'crs_glb':'EPSG:32649 easting/northing minus 758940/2474080; relative Z'}
 new_f.append({'type':'Feature','properties':props,'geometry':mapping(to_geo(x['polygon_new']))})

patch_features=[]
for x in source_patch_info:
 props={'model_node':x['properties']['name'],'asset':'lakeside_pavement_joint','source_geometry':'BNBU_v71_CONNECTED_LAKEFRONT.glb source mesh unchanged',
  'source_photo':'https://co.bnbu.edu.cn/en/info/1131/2702.htm','source_2025_map':'https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg',
  'source_type':'v71 parent-model same-Z hardscape join; photos support typology not surveyed position',
  'confidence_xy':'UNSURVEYED_PARENT_MODEL','confidence_z':'UNSURVEYED_PARENT_RELATIVE_Z',
  'relative_z_min':x['properties']['model_bottom_z'],'relative_z_max':x['properties']['model_top_z'],
  'original_top_area_model_m2':x['properties']['patch_area_model_m2'],'footprint_symmetric_difference_model_m2':0.0,
  'boundary_max_displacement_model_m':0.0,
  'is_surveyed':0,'is_glass':0,'is_routable':0,'metric_birdstrike_eligible':0,'crs_gis':'EPSG:4326',
  'crs_glb':'EPSG:32649 easting/northing minus 758940/2474080; relative Z'}
 patch_features.append({'type':'Feature','properties':props,'geometry':x['geometry']})

# Remove active unsurveyed CTV geometry and all 5 active GIS claims.
base=json.loads((I/'BNBU_v64_ACTIVE.geojson').read_text('utf8'))
base_nodes=[f['properties'].get('model_node','') for f in base['features']]
assert CTV_GIS_NODES.issubset(base_nodes),CTV_GIS_NODES-set(base_nodes)
ctv_features=[f for f in base['features'] if f['properties'].get('model_node') in CTV_GIS_NODES]
(D/'BNBU_v75_QUARANTINED_CTV_NOT_SURVEYED.geojson').write_text(json.dumps({'type':'FeatureCollection','features':ctv_features},ensure_ascii=False,indent=2),'utf8')
base['features']=[f for f in base['features'] if f['properties'].get('model_node') not in CTV_GIS_NODES]+new_f+patch_features
base['name']='BNBU v75 consolidated v64 terrain, v71 source-grade lakeside joints, and 37 retopologized opaque trim meshes; no measured location correction'
assert len(base['features'])==531-5+37+2==565,len(base['features'])
(D/'BNBU_v75_ACTIVE.geojson').write_text(json.dumps(base,ensure_ascii=False,indent=1),'utf8')

shutil.copy2(I/'BNBU_v64_EDITABLE_GIS.gpkg',D/'BNBU_v75_EDITABLE_GIS.gpkg')
gpkg=D/'BNBU_v75_EDITABLE_GIS.gpkg'
for layer in ['v53_CTV_CC401_SIDEHOUSE_AND_ACCESS','v54_ACTIVE_CTV_ACCESS_CONNECTED']:
 assert layer in fiona.listlayers(gpkg)
 fiona.remove(gpkg,layer=layer,driver='GPKG')

# All new GIS features share uniform record schema for two independent layers.
fields={k:('int' if isinstance(v,int) else 'float' if isinstance(v,float) else 'str') for k,v in new_f[0]['properties'].items()}
def write_gpkg(layer,arr):
 with fiona.open(gpkg,'w',layer=layer,driver='GPKG',schema={'geometry':'MultiPolygon','properties':fields},crs=CRS.from_epsg(4326)) as ds:
  for feat in arr:
   g=shape(feat['geometry']);ds.write({'geometry':mapping(g if isinstance(g,MultiPolygon) else MultiPolygon([g])),
    'properties':{k:feat['properties'].get(k) for k in fields}})
write_gpkg('v75_existing_opaque_storey_trims_closed',new_f)
write_gpkg('v75_v71_source_grade_lrc_pavement_joins',patch_features)
assert len(fiona.listlayers(gpkg))==141

ns='http://www.opengis.net/kml/2.2';K=lambda x:'{'+ns+'}'+x;ET.register_namespace('',ns)
tree=ET.parse(I/'BNBU_v64_ACTIVE.kml');root=tree.getroot(); doc=root.find(K('Document'))
assert doc is not None
for p in list(doc):
 if p.tag==K('Placemark') and (p.findtext(K('name')) or '') in CTV_GIS_NODES:doc.remove(p)
assert len(doc.findall(K('Placemark')))==526
for f in new_f+patch_features:
 p=f['properties'];g=shape(f['geometry']);pm=ET.SubElement(doc,K('Placemark'))
 ET.SubElement(pm,K('name')).text=p['model_node']
 ET.SubElement(pm,K('description')).text=p['source_type']+'; NO surveyed location/height. Not routable or glass.'
 ex=ET.SubElement(pm,K('ExtendedData'))
 for field in ('asset','source_geometry','confidence_xy','confidence_z','is_surveyed','is_glass','is_routable'):
  a=ET.SubElement(ex,K('Data'),name=field);ET.SubElement(a,K('value')).text=str(p[field])
 for poly in (g.geoms if isinstance(g,MultiPolygon) else [g]):
  host=ET.SubElement(pm,K('MultiGeometry')) if isinstance(g,MultiPolygon) else pm
  po=ET.SubElement(host,K('Polygon'))
  for ring,kind in [(poly.exterior,'outerBoundaryIs')]+[(r,'innerBoundaryIs') for r in poly.interiors]:
   ringel=ET.SubElement(ET.SubElement(po,K(kind)),K('LinearRing'))
   ET.SubElement(ringel,K('coordinates')).text=' '.join(f'{a:.10f},{b:.10f},0' for a,b in ring.coords)
tree.write(D/'BNBU_v75_ACTIVE.kml',encoding='utf8',xml_declaration=True)
assert len(doc.findall(K('Placemark')))==565
report={'version':'v75','parent':'v64 plus source-matched v71 from v74','scene_meshes_parent':1381,'scene_meshes_new':1379,
 'unchanged_node_count':1340,'repaired_preexisting_opaque_meshes':37,'quarantined_active_unverified_ctv_meshes':4,
 'quarantined_ctv_gis_features':5,'source_v71_lrc_pavement_join_meshes_added':2,'source_v71_patch_normals_corrected':2,
 'new_watertight_opaque':all(x['mesh'].is_watertight for x in replacements),
 'repaired_old_top_area_sum_m2':float(sum(x['polygon_parent'].area for x in replacements)),
 'retopology_max_symdiff_model_m2':max(x['symdiff_m2'] for x in replacements),
 'retopology_max_boundary_displacement_model_m':max(x['hausdorff_m'] for x in replacements),
 'topology_clearance_model_m':TOPOLOGY_CLEARANCE,
 'new_gpkg_layers':len(fiona.listlayers(gpkg)), 'active_geojson_features':len(base['features']), 'active_kml_placemarks':len(doc.findall(K('Placemark'))),
 'crs_glb':'UTM EPSG:32649, local XY subtract (758940,2474080); Z model relative, not surveyed',
 'crs_gis':'EPSG:4326','no_new_glazing_or_tree_or_roof_machinery':True,'surveys_new':0,
 'excluded_legacy_fake_glazing_bands':690,'excluded_guess_glass_rails':6,'excluded_guess_roof_rooms':5,
 'residential_retouched':[x['new'] for x in replacements],
 'removed_unverified_meshes':CTV_MESHES,'model_evidence_limit':'hand drawn and photo typologies are not orthorectified or registered',
 'dsm_reference_from_v74_separate_not_merged':True}
(Q/'v75_build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='residential_retouched'},ensure_ascii=False,indent=2))