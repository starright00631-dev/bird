#!/usr/bin/env python3
"""Actual geometry: LRC existing circular skylight glass closure.

The glass infill fills the already-present circular roof hole using the v10 archived
skylight feature, the existing v75 LRC glazing rim, and the shapes of v75 opaque
arched mullions. It is one continuous material layer with NO fictional pane grid.
The rib shape, XY and z are inherited MODEL proxies, not registered photographs.
"""
from pathlib import Path
import json, shutil, xml.etree.ElementTree as ET, math
import numpy as np, trimesh, fiona
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, MultiPolygon, mapping, shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer
from fiona.crs import CRS

R=Path(__file__).resolve().parents[1]; I=R/'input'; O=R/'model'; D=R/'data'; Q=R/'qa'; V=R/'reference'
for d in (O,D,Q):d.mkdir(parents=True,exist_ok=True)
parent=trimesh.load(I/'BNBU_v75_FULL_EDITABLE.glb', force='scene',process=False)
original=list(parent.graph.nodes_geometry)
assert len(original)==1379

def worldmesh(n):
 tf,geom=parent.graph[n];m=parent.geometry[geom].copy();m.apply_transform(tf);return m
rim=worldmesh('LRC_SKYLIGHT_RIM');oldroof=worldmesh('ROOF_DECK_LRC')
upper=rim.vertices[rim.faces]
top=np.ptp(upper[:,:,2],axis=1)<1e-5
zrim=float(rim.vertices[:,2].max())
# Extract original interior ring from actual GLB top faces (not freehand re-drawing).
from shapely.ops import unary_union
rim_polygon=unary_union([Polygon(tr[:,:2]) for tr in upper[top] if Polygon(tr[:,:2]).area>1e-9])
assert rim_polygon.geom_type=='Polygon' and len(rim_polygon.interiors)==1
ring=np.array(rim_polygon.interiors[0].coords[:-1],dtype=float)
assert len(ring)==256,(len(ring))
center=np.array([rim_polygon.interiors[0].centroid.x,rim_polygon.interiors[0].centroid.y])
radii=np.linalg.norm(ring-center,axis=1)
R_open=float(np.max(radii)+0.00005);assert 9.98<R_open<10.06
assert np.ptp(radii)<0.005
# Preserve the parent roof's original clear opening; no cutting/reinventing the roof.
v=oldroof.vertices[oldroof.faces]
h=(np.ptp(v[:,:,2],axis=1)<1e-5)&(abs(v[:,:,2].mean(axis=1)-oldroof.vertices[:,2].max())<1e-4)
roof_foot=unary_union([Polygon(t[:,:2]) for t in v[h] if Polygon(t[:,:2]).area>1e-9]); assert len(roof_foot.interiors)==1
assert roof_foot.interiors[0].centroid.distance(rim_polygon.interiors[0].centroid)<0.004
assert Polygon(ring).difference(Polygon(roof_foot.interiors[0])).area<1e-6
# Two pre-existing opaque arch ribs define the only available 3D curvature evidence.
RIBS=['V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_EASTWEST', 'V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_NORTHSOUTH']
rv=np.vstack([worldmesh(n).vertices for n in RIBS]);rr=np.linalg.norm(rv[:,:2]-center,axis=1)
# Statistical centerline proxy with taper restricted to the last 6% of span.
radial_grid=[0.0];z_grid=[float(np.percentile(rv[rr<1.6,2],65))-0.04];samples=[]
for radius in np.arange(1.0,9.51,.5):
 sel=(rr>radius-.25)&(rr<=radius+.25)
 if sel.sum()<8: continue
 med=float(np.median(rv[sel,2]));samples.append({'radius_model_m':float(radius),'rib_median_model_z':med,'count':int(sel.sum())})
 radial_grid.append(float(radius));z_grid.append(med-.055)
# Only this near-rim transition cannot be determined directly from photographs.
# Continuously join existing model's circular rim, do not claim the collar is measured.
assert radial_grid[-1]==9.5
z_grid[-1]=max(z_grid[-1],zrim+1.40)
radial_grid.extend([9.75,R_open]);z_grid.extend([zrim+.97,zrim-.010])
# Enforce nonincreasing roof elevation as one moves outwards, avoid self-intersection.
for j in range(1,len(z_grid)):z_grid[j]=min(z_grid[j],z_grid[j-1]-0.0001)
curve=PchipInterpolator(radial_grid,z_grid,extrapolate=False)
# Build a continuous, 36mm solid (top,bottom,edge), not an array of window panes.
N=len(ring);rings=np.linspace(0.0,1.0,35)[1:];grid=[]
for frac in rings:
 xy=center+(ring-center)*frac
 rad=np.linalg.norm(xy-center,axis=1)
 zz=curve(rad)
 grid.append(np.column_stack((xy,zz)))
grid=np.asarray(grid);assert np.isfinite(grid).all()
depth=0.036
vt=np.concatenate([np.array([[center[0],center[1],float(curve(0))]]),grid.reshape(-1,3)],axis=0)
vb=vt.copy();vb[:,2]-=depth
verts=np.vstack([vt,vb]);T=len(vt)
faces=[]
# Ring winding in original data isn't guaranteed, so robustly repair normals after construction.
for j in range(N):faces.append([0,1+j,1+(j+1)%N])
for ri in range(len(rings)-1):
 a=1+ri*N;b=1+(ri+1)*N
 for j in range(N):
  k=(j+1)%N
  faces.extend([[a+j,b+j,b+k],[a+j,b+k,a+k]])
faces=np.asarray(faces,dtype=int)
faces=np.vstack([faces,faces[:,::-1]+T])
for j in range(N):
 a=1+(len(rings)-1)*N+j;b=1+(len(rings)-1)*N+(j+1)%N
 faces=np.vstack([faces,[a,b,b+T],[a,b+T,a+T]])
glass=trimesh.Trimesh(vertices=verts,faces=faces,process=True)
glass.fix_normals()
if glass.volume<0:glass.invert()
assert glass.is_watertight and glass.is_winding_consistent and glass.volume>0
assert len(glass.faces)>15000
# Transparent and physically descriptive PBR material; viewer additionally categorizes by name.
mat=trimesh.visual.material.PBRMaterial(name='LRC_SKYLIGHT_CONTINUOUS_GLASS_UNMEASURED',
 baseColorFactor=[0.43,0.75,0.89,0.42],metallicFactor=0.04,roughnessFactor=0.18,
 alphaMode='BLEND',doubleSided=True)
glass.visual=trimesh.visual.TextureVisuals(material=mat)
NAME='V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED'
output=trimesh.Scene()
for n in original:
 tf,gn=parent.graph[n]
 output.add_geometry(parent.geometry[gn].copy(),node_name=n,geom_name=n,transform=tf)
output.add_geometry(glass,node_name=NAME,geom_name=NAME)
assert len(output.graph.nodes_geometry)==1380
(O/'BNBU_v76_FULL_EDITABLE.glb').write_bytes(output.export('glb'))
only=trimesh.Scene();only.add_geometry(glass,node_name=NAME,geom_name=NAME)
(O/'BNBU_v76_SKYLIGHT_GLASS_ONLY.glb').write_bytes(only.export('glb'))

# Compare archived presence with current model; v10 footprint was an illustrated proxy.
ref=json.loads((V/'v9_LRC_skylight.geojson').read_text('utf8'))['features'][0]
assert ref['properties']['kind']=='roof_glass_skylight' and ref['properties']['geometry_measured']==False
local_to_gps=Transformer.from_crs(32649,4326,always_xy=True)
polygon=Polygon(ring)
geom=shp_transform(lambda x,y,z=None:local_to_gps.transform(np.asarray(x)+758940,np.asarray(y)+2474080), polygon)
properties={
 'model_node':NAME,'asset':'glazed_skylight_continuous','location':'Phase I LRC existing circular skylight',
 'source_presence':'BNBU v10 archived school-official roof photo reference; LRC architectural skylight description',
 'source_official_photo_archive':ref['properties']['source_url'],
 'source_architectural_description':'https://www.stefanogambacciani.com/copia-di-the-next-future-hotel-1',
 'source_2025_handdrawn_structural':'https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg',
 'source_xy':'Existing v75 GLB LRC_SKYLIGHT_RIM, inner perimeter 256 vertices',
 'source_z':'Existing v75 GLB V26_LRC_OVAL_SKYLIGHT_OPAQUE_MULLIONS_* model rib curves',
 'confidence_presence':'MODERATE_ARCHIVE_AND_ARCHITECTURE_TEXT',
 'confidence_xy':'LOW_PROXY_INHERITED_NOT_ORTHORECTIFIED',
 'confidence_z':'LOW_RIB_INTERPOLATED_NOT_PHOTO_REGISTERED',
 'modelled_edge':'tapered last 0.52m to inherited rim, NOT measured',
 'is_surveyed':0,'is_osm_way':0,'is_glass':1,'metric_birdstrike_eligible':0,'is_routable':0,
 'horizontal_crs_local':'EPSG:32649 offset (758940,2474080)','gis_crs':'EPSG:4326',
 'vertical_reference':'model-relative unknown absolute datum','model_z_min':float(glass.bounds[0,2]),
 'model_z_max':float(glass.bounds[1,2]),'plan_area_model_m2':float(polygon.area),
 'surface_area_model_m2_not_real_measured':float(glass.area/2), 'new_pane_grid_count':0}
feature={'type':'Feature','properties':properties,'geometry':mapping(geom)}
oldjs=json.loads((I/'BNBU_v75_ACTIVE.geojson').read_text('utf8'))
assert len(oldjs['features'])==565
oldjs['features'].append(feature)
oldjs['name']='BNBU v76 (v75 inherited, one evidence-bounded LRC skylight glass geometry, not surveyed)'
(D/'BNBU_v76_ACTIVE.geojson').write_text(json.dumps(oldjs,indent=1,ensure_ascii=False),'utf8')
shutil.copy2(I/'BNBU_v75_EDITABLE_GIS.gpkg',D/'BNBU_v76_EDITABLE_GIS.gpkg')
schema={'geometry':'Polygon','properties':{k:'int' if isinstance(v,int) else 'float' if isinstance(v,float) else 'str' for k,v in properties.items()}}
with fiona.open(D/'BNBU_v76_EDITABLE_GIS.gpkg','w',driver='GPKG',layer='v76_existing_LRC_atrium_skylight_glazing_nonmetric',schema=schema,crs=CRS.from_epsg(4326)) as dst:
 dst.write({'type':'Feature','geometry':mapping(geom),'properties':properties})
ns='http://www.opengis.net/kml/2.2'; K=lambda x:'{'+ns+'}'+x;ET.register_namespace('',ns)
tree=ET.parse(I/'BNBU_v75_ACTIVE.kml');doc=tree.getroot().find(K('Document'))
assert len(doc.findall(K('Placemark')))==565
placemark=ET.SubElement(doc,K('Placemark'))
ET.SubElement(placemark,K('name')).text=NAME
ET.SubElement(placemark,K('description')).text='Existing LRC circular skylight continuous glass model; unsurveyed radial roof interpolation. Not metric bird strike glass area.'
for k in ('source_xy','source_z','confidence_xy','confidence_z','vertical_reference','metric_birdstrike_eligible','is_glass'):
 data=ET.SubElement(ET.SubElement(placemark,K('ExtendedData')) if placemark.find(K('ExtendedData')) is None else placemark.find(K('ExtendedData')),K('Data'),{'name':k})
 ET.SubElement(data,K('value')).text=str(properties[k])
poly=ET.SubElement(placemark,K('Polygon'));edge=ET.SubElement(poly,K('outerBoundaryIs'));lr=ET.SubElement(edge,K('LinearRing'))
ET.SubElement(lr,K('coordinates')).text=' '.join(f'{x:.11f},{y:.11f},0' for x,y in geom.exterior.coords)
tree.write(D/'BNBU_v76_ACTIVE.kml',encoding='utf8',xml_declaration=True)

report={'version':'v76','parent_version':'v75','parent_meshes':1379,'result_meshes':1380,
 'added_existing_covered_glass_surface':1,'new_glass_panels':0,'observational_presence':'archived school roof photo URL and LRC architectural note',
 'new_mesh_triangles':int(len(glass.faces)),'new_mesh_vertices':int(len(glass.vertices)),
 'glass_solid_watertight':bool(glass.is_watertight),'glass_solid_winding_consistent':bool(glass.is_winding_consistent),
 'glass_solid_volume_positive':bool(glass.volume>0),
 'plan_area_model_m2_not_surveyed':polygon.area, 'glass_proxy_surface_area_model_m2_not_surveyed':glass.area/2,
 'rim_center_model_xy':center.tolist(),'rim_radius_model_m':R_open,
 'sampled_ribs':RIBS, 'radial_guide_points_model':list(zip(radial_grid,z_grid)),'radial_source_samples':samples,
 'model_crs':'EPSG:32649 minus 758940,2474080; z model-relative','gis_crs':'EPSG:4326',
 'archive_v10_skylight_proxy_area_m2':float(shape(ref['geometry']).area),
 'is_orthorectified':False,'is_surveyed':False,'eligible_for_glass_area_risk':False,
 'gpkg_layers':len(fiona.listlayers(D/'BNBU_v76_EDITABLE_GIS.gpkg')),
 'geojson_features':len(oldjs['features']),'kml_placemarks':len(doc.findall(K('Placemark'))),
 'no_new_random_panes_rails_trees_roof_equipment':True,
 'missing_survey':'camera pose / photogrammetry, ground way nodes, DEM/vertical survey'}
(Q/'v76_build.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['radial_source_samples','radial_guide_points_model']},indent=2,ensure_ascii=False))