"""BNBU v72 source-sampled connection profiles; images do NOT confer metric poses.

Generate four display-only guardrail paths on two *existing* 3D connectors:
east-lake ramp: exact perimeter XY + original upper skin Z from 122 source
vertices; LRC exterior stair: 19 actual tread top levels, 2 x-edge sides.
No new road, path, bridge, stair or glass surface geometry.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform,nearest_points

ROOT=Path(__file__).resolve().parent
GENERATED=ROOT/"generated"
MODEL=GENERATED/"BNBU_v71_CONNECTED_LAKEFRONT.glb"
GIS=GENERATED/"BNBU_v66_RESOLVED_REFERENCES.geojson"
AUDIT=GENERATED/"BNBU_v71_JUNCTION_AUDIT.geojson"
PHOTOS=ROOT/"connection_photos_v72.json"
OUTPUT=GENERATED/"BNBU_v72_SOURCE_ELEVATION_PROFILES.json"
XY=(758940.0,2474080.0)
TO_UTM=Transformer.from_crs("EPSG:4326","EPSG:32649",always_xy=True).transform
RAMP="V54_LAKE00_EAST_WATER_CROSSING_SHORE_RAMP_INFERRED_ENDPOINT_MATCH"
STAIR="V48_LRC_EXISTING_18_TREAD_EXTERIOR_STAIR_CONNECTED_NOT_SURVEYED"
DECK="V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE"

def digest(blob):return hashlib.sha256(blob).hexdigest()
def decode(blob):
 assert blob[:4]==b"glTF" and struct.unpack_from("<II",blob,4)==(2,len(blob))
 n,t=struct.unpack_from("<I4s",blob,12);assert t==b"JSON"
 doc=json.loads(blob[20:20+n]);offset=20+n
 ln,kind=struct.unpack_from("<I4s",blob,offset);assert kind==b"BIN\0"
 return doc,blob[offset+8:offset+8+ln]
def mesh_xyz(doc,binary,node):
 lookup={n["name"]:n for n in doc["nodes"] if n.get("name") and "mesh" in n}
 assert node in lookup,node
 prim=doc["meshes"][lookup[node]["mesh"]]["primitives"][0]
 acc=doc["accessors"][prim["attributes"]["POSITION"]]
 bv=doc["bufferViews"][acc["bufferView"]]
 assert acc["componentType"]==5126 and acc["type"]=="VEC3"
 offset=bv["byteOffset"]+acc.get("byteOffset",0)
 stride=bv.get("byteStride",12)
 return np.array([struct.unpack_from("<fff",binary,offset+stride*i)
                  for i in range(acc["count"])],dtype=np.float64)
def feature(gis,name):
 hits=[transform(TO_UTM,shape(f["geometry"])) for f in gis["features"]
       if (f["properties"].get("render_model_node") or f["properties"].get("model_node"))==name]
 assert hits,(name,"missing source polygon")
 return max(hits,key=lambda g:g.area)
def ramp_lines(outer,vertices):
 if outer.geom_type=="MultiPolygon":outer=max(outer.geoms,key=lambda p:p.area)
 coords=np.array([[x-XY[0],y-XY[1]] for x,y in list(outer.exterior.coords)[:-1]])
 imin=int(np.argmin(coords[:,0]));imax=int(np.argmax(coords[:,0]))
 def route(step):
  out=[];i=imin
  while True:
   out.append(coords[i])
   if i==imax:break
   i=(i+step)%len(coords)
   assert len(out)<len(coords)+1
  return np.array(out)
 result=[]
 # The polygon boundary has two short transverse END CAPS. Never rail across\n # an entrance: trim the first cap from north side, last cap from south side.\n for side,poly in zip(("north_edge","south_edge"),(route(1)[1:],route(-1)[:-1])):
  # The outer polygon was generated from this exact mesh. Verify every
  # point is traceably within 0.05 model units of its original XY source.
  d=np.linalg.norm(poly[:,None,:]-vertices[None,:,:2],axis=2)
  assert float(d.min(axis=1).max())<.05
  z=[]
  for i in range(len(poly)):
   nearby=vertices[d[i]<.08]
   assert len(nearby)>0
   z.append(float(np.max(nearby[:,2])))  # top, not -0.17m underside
  pts=np.column_stack([poly,z])
  assert .025<=pts[:,2].min()<.12 and .87<pts[:,2].max()<=.92
  # Keep ends open so the rail does not block the landfall or deck entrance.
  # The two side arcs contain short end caps; sample without first 1m.
  from shapely.geometry import LineString
  line=LineString([(x,y) for x,y in poly])
  length=line.length
  t=np.cumsum(np.r_[0,np.linalg.norm(np.diff(poly,axis=0),axis=1)])
  samples=np.linspace(1.1,length-1.1,int((length-2.2)/.48)+1)
  coords3=[]
  for f in samples:
   x=float(np.interp(f,t,poly[:,0]))
   y=float(np.interp(f,t,poly[:,1]))
   zz=float(np.interp(f,t,np.array(z)))
   coords3.append([round(x,4),round(y,4),round(zz,4)])
  result.append({"id":"RAMP_"+side,"source_node":RAMP,"category":"bridge_to_land_slope",
      "model_surface_xyz":coords3,"source_boundary_vertices":len(poly),
      "draw_as":"optional_illustrative_metal_guardrail",
      "photo_support":["P02","P04","P08"],"height_above_surface_model_units":.83,
      "guardrail_height_is_not_surveyed":True,"ground_truth_route":False})
 return result
def stair_lines(vertices):
 result=[]
 for side,x in (("west_side",float(np.min(vertices[:,0]))),
                ("east_side",float(np.max(vertices[:,0])))):
  sub=vertices[np.abs(vertices[:,0]-x)<.03]
  by_y={}
  for _,yy,z in sub:
   key=round(float(yy),3)
   by_y[key]=max(by_y.get(key,-1e6),float(z))
  series=sorted(by_y.items(),key=lambda item:-item[0])
  assert len(series)==19 and abs(series[0][1]-.172)<.02 and abs(series[-1][1]-3.1)<.02
  coords=[[round(x,4),round(y,4),round(z,4)] for y,z in series]
  result.append({"id":"STAIR_"+side,"source_node":STAIR,"category":"building_to_ground_stair",
   "model_surface_xyz":coords,"source_top_steps":19,
   "draw_as":"optional_illustrative_stair_handrail",
   "photo_support":["P05","P06","P07","P12"],
   "height_above_surface_model_units":.86,"guardrail_height_is_not_surveyed":True,
   "ground_truth_route":False})
 return result
def grade_markers(audit):
 output=[]
 for i,f in enumerate(audit["features"]):
  p=f["properties"]
  if p.get("junction_status")!="vertical_mismatch_unresolved":continue
  if p["model_top_offset_m"]<.10:continue
  geom=transform(TO_UTM,shape(f["geometry"]))
  pt=geom.centroid
  lo=min(p["source_z_top_a"],p["source_z_top_b"]);hi=max(p["source_z_top_a"],p["source_z_top_b"])
  output.append({"id":"GRADE_MISMATCH_"+str(i),"reference_nodes":[p["source_node_a"],p["source_node_b"]],
    "local_x":round(pt.x-XY[0],4),"local_y":round(pt.y-XY[1],4),
    "z_low":lo,"z_high":hi,"delta":round(hi-lo,4),
    "status":"3D elevation mismatch marker ONLY — NOT A CONNECTOR",
    "does_not_certify_accessibility":True})
 assert len(output)==3
 return output

def build():
 blob=MODEL.read_bytes();raw=GIS.read_bytes()
 doc,binary=decode(blob)
 assert len(doc["meshes"])==1379
 gis=json.loads(raw);audit=json.loads(AUDIT.read_text());photos=json.loads(PHOTOS.read_text())
 assert len(gis["features"])==522 and len(audit["features"])==11
 assert len(photos["photos"])==16 and len({x["image_url"] for x in photos["photos"]})==16
 rv=mesh_xyz(doc,binary,RAMP);sv=mesh_xyz(doc,binary,STAIR)
 assert len(rv)==122 and len(sv)==76
 profiles=ramp_lines(feature(gis,RAMP),rv)+stair_lines(sv)
 markers=grade_markers(audit)
 result={"version":"v72","scene_glb_sha256":digest(blob),"source_gis_sha256":digest(raw),
 "source_profile_geometry":"EXACT SOURCE MODEL XYZ, DISPLAY-ONLY HANDRAIL HEIGHTS ARE HYPOTHESES",
 "original_source_meshes":1377,"v71_scene_meshes":1379,"source_gis_features":522,
 "photo_count_inspected":len(photos["photos"]),"physically_new_road_meshes":0,
 "physically_new_bridge_meshes":0,"physically_new_stair_meshes":0,
 "rail_profiles":profiles,"height_disagreement_markers":markers,
 "reference_photo_ids":[x["id"] for x in photos["photos"]],
 "no_glass_birdstrike_metric_area":True,
 "caution":["Source model vertical coordinates are model-relative not surveyed elevations.",
            "Handrails display type and topology supported by photos, NOT measured 0.83m / 0.86m height.",
            "LRC and ramp exact camera-to-image matching not completed.",
            "Off-campus Chicago UIC content explicitly rejected; original 16 BNBU images are individually referenced.",
            "Unknown western boardwalk landing grade remains unresolved; vertical diagnostics are not a constructed ramp."]}
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"profiles":len(profiles),"points":[len(x["model_surface_xyz"]) for x in profiles],
 "grade_disagreements":[x["delta"] for x in markers],"photos":len(photos["photos"])},indent=2))
 return result
if __name__=="__main__":build()
