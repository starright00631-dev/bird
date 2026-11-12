#!/usr/bin/env python3
"""BNBU v77: phase-II round pavilion roof intersection repair + photo-derived paving seams.
No windows, new glazing, random trees or roof equipment. Preserve v76 elsewhere exactly.
BNBU official landscape photo (publication date unspecified) confirms square rooftop pavers and central raised disk;
seam count, seam dimensions, and 3D material offsets are nonmetric hypotheses.
"""
from pathlib import Path
import json,shutil,xml.etree.ElementTree as ET
import numpy as np,trimesh,fiona,shapely
from shapely.geometry import LineString,Polygon,Point,MultiPolygon,mapping
from shapely.ops import unary_union,transform as shptr
from pyproj import Transformer
from fiona.crs import CRS

R=Path(__file__).resolve().parents[1];I=R/'input';O=R/'model';D=R/'data';Q=R/'qa'
for p in (O,D,Q):p.mkdir(parents=True,exist_ok=True)
SRC='https://www.bnbu.edu.cn/en/campus_life/Landscape_and_Facilities/1.htm'
OFFICIALMAP='https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg'
scene=trimesh.load(I/'BNBU_v76_FULL_EDITABLE.glb',force='scene',process=False)
original=list(scene.graph.nodes_geometry)
assert len(original)==1380
CENTRAL='V24_P2_CIRCULAR_COMMONS_09_LOW_CENTRAL_ROOF_CIRCLE'
SQUARE='V58_P2_ROUND_COMMONS_SQUARE_INLAID_ROOF_FIELD_PHOTO_TYPE_UNSURVEYED'
ROOF='V24_P2_CIRCULAR_COMMONS_08_OPAQUE_ROOF_PERIMETER'
assert all(n in original for n in [CENTRAL,SQUARE,ROOF])
def meshworld(name):
    tf,k=scene.graph[name];g=scene.geometry[k].copy();g.apply_transform(tf);return g
oldcap=meshworld(CENTRAL); square=meshworld(SQUARE); roof=meshworld(ROOF)
center=oldcap.bounds.mean(axis=0)[:2]
sqcenter=square.bounds.mean(axis=0)[:2]
assert np.linalg.norm(center-sqcenter)<.05
z_pavement=float(square.bounds[1,2])
# Existing cap should rest on the established square paving upper plane, rather
# than burying its 3D bottom inside the square solid; no size guessed anew.
zdiff=float(z_pavement-oldcap.bounds[0,2]-0.006)
assert .02<zdiff<.15
cap=oldcap.copy();cap.apply_translation([0,0,zdiff])
assert np.array_equal(cap.faces,oldcap.faces)
assert cap.is_watertight and cap.is_winding_consistent
radius=float(np.linalg.norm(oldcap.vertices[:,:2]-center,axis=1).max())
assert 3.2<radius<3.5
# Grid spacing is an unrectified visual approximation of the *observed* roof
# paving seams, not a tile count or centimeter-scale field measurement.
x0,y0=square.bounds[0,:2];x1,y1=square.bounds[1,:2]
assert 15<x1-x0<18 and 15<y1-y0<18
pad=0.55; xs=np.linspace(x0+pad,x1-pad,6)[1:-1];ys=np.linspace(y0+pad,y1-pad,6)[1:-1]
q=Polygon([(x0+pad,y0+pad),(x1-pad,y0+pad),(x1-pad,y1-pad),(x0+pad,y1-pad)])
exclusion=Point(center).buffer(radius+0.16,quad_segs=64)
# One edit-ready non-glass seam group per direction. Deduplicate crossings.
vlines=unary_union([LineString([(float(x),y0+pad),(float(x),y1-pad)]).buffer(.042,cap_style=2) for x in xs])
hlines=unary_union([LineString([(x0+pad,float(y)),(x1-pad,float(y))]).buffer(.042,cap_style=2) for y in ys])
vertical=vlines.intersection(q).difference(exclusion)
horizontal=hlines.intersection(q).difference(exclusion).difference(vertical.buffer(0))
assert vertical.is_valid and horizontal.is_valid and vertical.area>0 and horizontal.area>0
assert vertical.intersection(horizontal).area<1e-7
# use original roof paving surface as Z origin, no new height datum.
z0=z_pavement+0.004;z1=z0+0.010

def extrude_polygon(p,z0,z1):
    vs=[];fs=[];indices={}
    def idx(x,y,z):
        key=(round(float(x),6),round(float(y),6),round(float(z),6))
        if key not in indices:indices[key]=len(vs);vs.append(key)
        return indices[key]
    tris=shapely.constrained_delaunay_triangles(p)
    for tr in tris.geoms:
        if not p.covers(tr.representative_point()):continue
        x=np.array(tr.exterior.coords[:3]);area=np.cross(x[1]-x[0],x[2]-x[0])
        if abs(area)<1e-10:continue
        if area<0:x=x[::-1]
        fs.append([idx(*u,z1) for u in x]);fs.append([idx(*u,z0) for u in x[::-1]])
    for ring in [p.exterior,*p.interiors]:
        for a,b in zip(list(ring.coords)[:-1],list(ring.coords)[1:]):
            fs.extend([[idx(*a,z0),idx(*b,z0),idx(*b,z1)],[idx(*a,z0),idx(*b,z1),idx(*a,z1)]])
    g=trimesh.Trimesh(vertices=np.array(vs),faces=np.array(fs,dtype=int),process=True)
    g.fix_normals();return g

def seal(p):
    polys=[p] if p.geom_type=='Polygon' else list(p.geoms)
    mesh=trimesh.util.concatenate([extrude_polygon(pp,z0,z1) for pp in polys if pp.area>1e-6])
    mesh.fix_normals()
    if mesh.volume<0:mesh.invert()
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    mesh.visual.vertex_colors=np.tile(np.array([123,110,94,255],dtype=np.uint8),(len(mesh.vertices),1))
    return mesh
nV='V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_NS_OPAQUE_UNREGISTERED'
nH='V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_EW_OPAQUE_UNREGISTERED'
gV=seal(vertical);gH=seal(horizontal)
new=trimesh.Scene()
for name in original:
    tf,k=scene.graph[name]
    if name==CENTRAL:
        tf=np.eye(4);g=cap
    else:g=scene.geometry[k].copy()
    new.add_geometry(g,node_name=name,geom_name=name,transform=tf)
new.add_geometry(gV,node_name=nV,geom_name=nV);new.add_geometry(gH,node_name=nH,geom_name=nH)
assert len(new.graph.nodes_geometry)==1382
(O/'BNBU_v77_FULL_EDITABLE.glb').write_bytes(new.export('glb'))
delta=trimesh.Scene()
for nm,g in [(CENTRAL,cap),(nV,gV),(nH,gH)]:delta.add_geometry(g,node_name=nm,geom_name=nm)
(O/'BNBU_v77_PHASEII_ROOF_EDIT_ONLY.glb').write_bytes(delta.export('glb'))
# Archive exact earlier cap so reconstruction is reversible.
archive=trimesh.Scene();archive.add_geometry(oldcap,node_name=CENTRAL,geom_name=CENTRAL)
(O/'BNBU_v77_ARCHIVED_ORIGINAL_CENTRAL_ROOF_CAP.glb').write_bytes(archive.export('glb'))

# GIS feature XY geometry is transformed from the inherited GLB (not a photo map).
T=Transformer.from_crs(32649,4326,always_xy=True)
def togeo(poly):return shptr(lambda x,y,z=None:T.transform(np.asarray(x)+758940,np.asarray(y)+2474080),poly)
capfoot=Point(center).buffer(radius,quad_segs=72)
recs=[]
for nm,p,kind in [(CENTRAL,capfoot,'existing_opaque_cap_z_contact_corrected'),(nV,vertical,'photo_typology_paving_seams_NS'),(nH,horizontal,'photo_typology_paving_seams_EW')]:
    props={'model_node':nm,'asset':kind,'building':'phaseII_round_pavilion','material':'opaque_non_glass',
    'source_official_photo':SRC,'source_official_photo_date':'NOT_PUBLISHED_IN_PHOTO_GALLERY','source_2025_handdrawn_structural':OFFICIALMAP,
    'source_geometry':'Inherited v76 square roof/cap XY and model-relative Z',
    'confidence_presence':'HIGH photo shows central disk and grid paving',
    'confidence_position':'LOW inherited proxy not orthorectified',
    'confidence_seam_count':'LOW approximate visual grid, count NOT measured',
    'confidence_height':'LOW model-relative only',
    'geo_reference':'GLB EPSG:32649 minus 758940,2474080, Z model relative; GIS EPSG:4326',
    'is_surveyed':0,'is_glass':0,'is_routable':0,'metric_birdstrike_eligible':0,
    'is_OSM_way':0,'model_area_m2_not_surveyed':float(p.area),
    'model_zmin':float(cap.bounds[0,2]) if nm==CENTRAL else z0,
    'model_zmax':float(cap.bounds[1,2]) if nm==CENTRAL else z1,
    'height_adjustment_model_m':zdiff if nm==CENTRAL else 0.0}
    recs.append({'type':'Feature','properties':props,'geometry':mapping(togeo(p))})
# GIS prior layer remains historical. Add v77 active correction that supersedes old cap geometry metadata.
shutil.copy2(I/'BNBU_v76_EDITABLE_GIS.gpkg',D/'BNBU_v77_EDITABLE_GIS.gpkg')
props=recs[0]['properties'];schema={'geometry':'MultiPolygon','properties':{k:'int' if isinstance(v,int) else 'float' if isinstance(v,float) else 'str' for k,v in props.items()}}
with fiona.open(D/'BNBU_v77_EDITABLE_GIS.gpkg','w',driver='GPKG',layer='v77_p2_roof_disk_contact_and_paver_seams_unsurveyed',schema=schema,crs=CRS.from_epsg(4326)) as w:
 for rec in recs:
    g=shapely.geometry.shape(rec['geometry']);g=g if isinstance(g,MultiPolygon) else MultiPolygon([g]);w.write({'geometry':mapping(g),'properties':rec['properties']})
oldjson=json.loads((I/'BNBU_v76_ACTIVE.geojson').read_text('utf8'))
assert len(oldjson['features'])==566
oldjson['features'].extend(recs);oldjson['name']='BNBU v77 with phase-II pavilion cap contact correction and nonmetric observed roof seam typology'
(D/'BNBU_v77_ACTIVE.geojson').write_text(json.dumps(oldjson,ensure_ascii=False,indent=1),'utf8')
ns='http://www.opengis.net/kml/2.2';K=lambda x:'{'+ns+'}'+x;ET.register_namespace('',ns)
tree=ET.parse(I/'BNBU_v76_ACTIVE.kml');doc=tree.getroot().find(K('Document'))
assert len(doc.findall(K('Placemark')))==566
for rec in recs:
    pm=ET.SubElement(doc,K('Placemark'));ET.SubElement(pm,K('name')).text=rec['properties']['model_node']
    ET.SubElement(pm,K('description')).text='v77 roof model geometry; photographed type but XY/grid spacing unregistered, not surveyed.'
    meta=ET.SubElement(pm,K('ExtendedData'))
    for k,v in rec['properties'].items():
      d=ET.SubElement(meta,K('Data'),{'name':str(k)});ET.SubElement(d,K('value')).text=str(v)
    g=shapely.geometry.shape(rec['geometry']);mg=ET.SubElement(pm,K('MultiGeometry'))
    for pol in ([g] if g.geom_type=='Polygon' else list(g.geoms)):
      shape=ET.SubElement(mg,K('Polygon'))
      for ring,tag in [(pol.exterior,'outerBoundaryIs')]+[(r,'innerBoundaryIs') for r in pol.interiors]:
        part=ET.SubElement(shape,K(tag));lr=ET.SubElement(part,K('LinearRing'))
        ET.SubElement(lr,K('coordinates')).text=' '.join(f'{x:.10f},{y:.10f},0' for x,y in ring.coords)
tree.write(D/'BNBU_v77_ACTIVE.kml',encoding='utf8',xml_declaration=True)
report={'version':'v77','parent':'v76','parent_meshes':1380,'output_meshes':1382,
 'modified_existing_cap_node':CENTRAL,'unchanged_original_nodes':1379,
 'photo_bounded_new_roof_seam_meshes':2,'new_mesh_triangle_count':int(len(gV.faces)+len(gH.faces)),
 'cap_relative_z_contact_correction_m':zdiff,'cap_footprint_original_retained':True,
 'original_roof_seam_count_is_measured':False,'approx_NS_seam_count':len(xs),'approx_EW_seam_count':len(ys),
 'new_seams_watertight':bool(gV.is_watertight and gH.is_watertight),
 'photo_source':SRC,'official_structural_illustration':OFFICIALMAP,
 'new_glass_panes':0,'new_glass_rails':0,'new_random_trees':0,'new_roof_machine_rooms':0,
 'GPKG_layers':len(fiona.listlayers(D/'BNBU_v77_EDITABLE_GIS.gpkg')),
 'geojson_features':len(oldjson['features']),'kml_placemarks':len(doc.findall(K('Placemark'))),
 'coordinate_basis':'local EPSG32649 minus (758940,2474080), non-geodetic relative Z; GIS EPSG4326',
 'unchanged_unregistered_roof_and_road_metrics':True,
 'missing':'Real orthophoto/photogrammetric camera, verified roof tile spacing, registered OSM way, terrain DEM, new Phase-II teaching complex ground truth'}
(Q/'v77_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))