#!/usr/bin/env python3
"""Constrained terrain facet refinement of four inherited unsurveyed BNBU v53 hills.

No new XY, hill placement, boundaries, summit heights, bridges, trees, facades,
or measured geography. Updates the actual GLB's top vertices, not a flat map.
Only smooths interior surfaces and clamps each changed Z to 0.35 model metres.
"""
from pathlib import Path
import json, shutil, xml.etree.ElementTree as ET
import numpy as np, trimesh, fiona
from scipy.sparse import coo_matrix
from shapely.geometry import shape, mapping, MultiPolygon
from fiona.crs import CRS

R=Path(__file__).resolve().parents[1]; I=R/'input'; D=R/'data'; M=R/'model'; Q=R/'qa'
for d in (D,M,Q):d.mkdir(exist_ok=True)
old=trimesh.load(I/'BNBU_v63_FULL_EDITABLE.glb',force='scene',process=False)
original=list(old.graph.nodes_geometry)
assert len(original)==1381
name_map={n:'V64_CONSTRAINED_RELIEF_'+n[len('V53_TERRAIN_RELIEF_'):] for n in original if n.startswith('V53_TERRAIN_RELIEF_')}
assert len(name_map)==4
model=trimesh.Scene(); archive=trimesh.Scene(); delta=trimesh.Scene()
modified=[]
for n in original:
 tf,k=old.graph[n];geom=old.geometry[k]
 if n not in name_map:
  model.add_geometry(geom.copy(),node_name=n,geom_name=n,transform=tf)
  continue
 archive.add_geometry(geom.copy(),node_name=n,geom_name=n,transform=tf)
 newmesh=geom.copy()
 v=newmesh.vertices.copy(); z=v[:,2].copy(); faces=newmesh.faces
 # Top-surface adjacency only: do not smooth side walls or the flat underside.
 topfaces=faces[geom.face_normals[:,2] > 0.08]
 ii=np.concatenate([topfaces[:,0],topfaces[:,1],topfaces[:,2],topfaces[:,1],topfaces[:,2],topfaces[:,0]])
 jj=np.concatenate([topfaces[:,1],topfaces[:,2],topfaces[:,0],topfaces[:,0],topfaces[:,1],topfaces[:,2]])
 adj=coo_matrix((np.ones(len(ii),dtype=np.uint8),(ii,jj)),shape=(len(v),len(v))).tocsr()
 adj.data[:]=1
 deg=np.asarray(adj.sum(axis=1)).ravel()
 # Fixed: all underside, shoreline/road interfaces, flat ground and summit.
 editable=(deg>=2)&(z>0.25)&(z<z.max()-0.05)
 assert editable.sum()>600
 z_work=z.copy()
 for iteration in range(12):
  neighbor=adj.dot(z_work)/np.maximum(1,deg)
  z_work[editable]+=0.30*(neighbor[editable]-z_work[editable])
 dz=np.zeros_like(z)
 raw=z_work[editable]-z[editable]
 # Hold signed top-surface volume roughly constant: pure smoothing must not shrink hills.
 tris=v[topfaces]
 area=.5*np.abs(np.cross(tris[:,1,:2]-tris[:,0,:2],tris[:,2,:2]-tris[:,0,:2]))
 weights=np.bincount(topfaces.ravel(),weights=np.repeat(area/3,3),minlength=len(v))
 lo,hi=-.7,.7
 for _ in range(36):
  offset=(lo+hi)*.5
  signed=np.dot(weights[editable],np.clip(raw+offset,-.35,.35))
  if signed<0:lo=offset
  else:hi=offset
 dz[editable]=np.clip(raw+(lo+hi)*.5,-.35,.35)
 v[:,2]+=dz
 newmesh.vertices=v
 assert newmesh.is_watertight and newmesh.is_winding_consistent and newmesh.volume>0,n
 assert np.array_equal(newmesh.vertices[:,:2],geom.vertices[:,:2])
 assert np.array_equal(newmesh.faces,geom.faces)
 assert np.isclose(v[:,2].max(),z.max()) and np.isclose(v[:,2].min(),z.min())
 assert np.max(np.abs(dz))<=0.35000001
 # Both winding and vertex coloring retained (the geometry is derived, not repainted).
 assert np.array_equal(geom.visual.vertex_colors,newmesh.visual.vertex_colors)
 old_res=adj.dot(z)/np.maximum(1,deg)-z
 new_res=adj.dot(v[:,2])/np.maximum(1,deg)-v[:,2]
 before=float(np.mean(np.abs(old_res[editable])));after=float(np.mean(np.abs(new_res[editable])))
 assert after < 0.92*before,(n,before,after)
 model.add_geometry(newmesh,node_name=name_map[n],geom_name=name_map[n],transform=tf)
 delta.add_geometry(newmesh.copy(),node_name=name_map[n],geom_name=name_map[n],transform=tf)
 modified.append({'parent_node':n,'model_node':name_map[n],'edited_vertices':int(np.count_nonzero(dz)),
  'original_vertices':len(geom.vertices),'triangles_preserved':len(faces),
  'max_abs_z_change_model_m':float(np.max(np.abs(dz))),
  'mean_abs_z_change_model_m':float(np.mean(np.abs(dz[editable]))),
  'curvature_lap_before':before,'curvature_lap_after':after,
  'curvature_improvement_fraction':float(1-after/before),
  'summit_relative_z':float(z.max()), 'min_relative_z':float(z.min())})

assert len(model.graph.nodes_geometry)==1381
(M/'BNBU_v64_FULL_EDITABLE.glb').write_bytes(model.export('glb'))
(M/'BNBU_v64_RELIEF_CORRECTIONS_ONLY.glb').write_bytes(delta.export('glb'))
(M/'BNBU_v64_ARCHIVED_V53_RELIEF.glb').write_bytes(archive.export('glb'))
source=json.loads((I/'BNBU_v63_ACTIVE.geojson').read_text('utf8'))
assert len(source['features'])==527
source_index={f['properties'].get('model_node'):f for f in source['features']}
features=[]
for item in modified:
 orig=source_index[item['parent_node']]
 props={'model_node':item['model_node'],'parent_node':item['parent_node'],
  'asset':'terrain_relief_reprofile','source_geometry':'BNBU_v63_FULL_EDITABLE.glb inherited v53 terrain mesh',
  'source_structure':'https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg',
  'source_photo':'https://www.bnbu.edu.cn/about_us/overview/introducing.htm',
  'geometry_rule':'top surface 12 iterations Laplacian, individual vertex Z shift <=0.35m; original XY/footprint fixed',
  'confidence_xy':'LOW inherited unsurveyed reference, not orthophoto',
  'confidence_z':'LOW relative model only; not DEM',
  'confidence_mesh_change':'HIGH verified 3D mesh topology and XY preserved',
  'is_surveyed':0,'is_dem':0,'is_road':0,'is_glass':0,'metric_birdstrike_eligible':0,
  'geometry_revision':'v64', 'max_z_edit_model_m':item['max_abs_z_change_model_m'],
  'mesh_relative_max_z':item['summit_relative_z'],
  'crs_glb':'EPSG:32649 offset 758940,2474080 / Z relative only', 'crs_gis':'EPSG:4326'}
 features.append({'type':'Feature','properties':props,'geometry':orig['geometry']})

shutil.copy2(I/'BNBU_v63_EDITABLE_GIS.gpkg',D/'BNBU_v64_EDITABLE_GIS.gpkg')
props=features[0]['properties'];schema={'geometry':'MultiPolygon','properties':{k:'int' if isinstance(v,int) else 'float' if isinstance(v,float) else 'str' for k,v in props.items()}}
with fiona.open(D/'BNBU_v64_EDITABLE_GIS.gpkg','w',driver='GPKG',layer='v64_four_actual_3D_hill_slope_refinements_not_DEM',schema=schema,crs=CRS.from_epsg(4326)) as dst:
 for f in features:
  g=shape(f['geometry'])
  dst.write({'geometry':mapping(g if isinstance(g,MultiPolygon) else MultiPolygon([g])),'properties':f['properties']})
source['features'].extend(features);source['name']='BNBU v64 campus + 4 actual 3D relief mesh refinements; non-surveyed'
(D/'BNBU_v64_ACTIVE.geojson').write_text(json.dumps(source,ensure_ascii=False,indent=1),'utf8')
ns='http://www.opengis.net/kml/2.2'; ET.register_namespace('',ns);K=lambda x:'{'+ns+'}'+x
tr=ET.parse(I/'BNBU_v63_ACTIVE.kml');doc=tr.getroot().find(K('Document'))
assert len(doc.findall(K('Placemark')))==527
for f in features:
 p=f['properties'];geometry=shape(f['geometry']);pm=ET.SubElement(doc,K('Placemark'))
 ET.SubElement(pm,K('name')).text=p['model_node']
 ET.SubElement(pm,K('description')).text='Constrained inherited hill triangle mesh smoothing; not a DEM, no new footprint or geodetic height.'
 ed=ET.SubElement(pm,K('ExtendedData'))
 for field in ('parent_node','geometry_revision','confidence_xy','confidence_z','is_surveyed','is_dem'):
  dt=ET.SubElement(ed,K('Data'),{'name':field});ET.SubElement(dt,K('value')).text=str(p[field])
 for pol in (geometry.geoms if isinstance(geometry,MultiPolygon) else [geometry]):
  g=ET.SubElement(pm,K('MultiGeometry'));pg=ET.SubElement(g,K('Polygon'))
  for ring,label in [(pol.exterior,'outerBoundaryIs')]+[(r,'innerBoundaryIs') for r in pol.interiors]:
   b=ET.SubElement(pg,K(label));l=ET.SubElement(b,K('LinearRing'))
   ET.SubElement(l,K('coordinates')).text=' '.join(f'{x:.10f},{y:.10f},0' for x,y in ring.coords)
tr.write(D/'BNBU_v64_ACTIVE.kml',encoding='utf8',xml_declaration=True)
report={'version':'v64','parent':'v63','v10_removed_unsupported':{'glass_bands':690,'glass_balustrades':6,'roof_service_rooms':5},
 'mesh_count':len(model.graph.nodes_geometry),'original_meshes_unchanged':1377,'actually_modified_hill_meshes':modified,
 'no_new_roads_windows_trees_or_rails':True,'is_surveyed':False,
 'GPKG_layers':len(fiona.listlayers(D/'BNBU_v64_EDITABLE_GIS.gpkg')),
 'GeoJSON_features':len(source['features']),'KML_placemarks':len(doc.findall(K('Placemark'))),
 'CRS':'3D EPSG:32649 minus (758940,2474080); GIS EPSG:4326, z MODEL RELATIVE'}
assert report['GPKG_layers']==141 and report['GeoJSON_features']==531 and report['KML_placemarks']==531
(Q/'v64_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='actually_modified_hill_meshes'},indent=2))
for m in modified:print(m)