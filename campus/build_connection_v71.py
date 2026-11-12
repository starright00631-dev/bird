"""BNBU v71: connect only two source-matched land-only promenade gaps.

Controls are precomputed by shortest-edge analysis of v66 GIS and versioned
separately. Every run validates source SHA256, XY, Z, actual water exclusion.
Never infer a bridge, road, building threshold or ramp from image type alone.
"""
from __future__ import annotations
import hashlib, json, math, struct
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import Polygon,LineString,shape,mapping
from shapely.ops import transform,nearest_points

ROOT=Path(__file__).resolve().parent
D=ROOT/"generated"
BASE=D/"BNBU_v69_WATERFRONT_REFINED.glb"
GIS=D/"BNBU_v66_RESOLVED_REFERENCES.geojson"
CONTROL=ROOT/"connection_v71_control.json"
OUT=D/"BNBU_v71_CONNECTED_LAKEFRONT.glb"
PATCH=D/"BNBU_v71_CONNECTION_PATCHES.geojson"
GRAPH=D/"BNBU_v71_JUNCTION_AUDIT.geojson"
META=D/"BNBU_v71_CONNECTION_PROVENANCE.json"
XY=(758940.0,2474080.0)
TO_UTM=Transformer.from_crs("EPSG:4326","EPSG:32649",always_xy=True).transform
TO_WGS=Transformer.from_crs("EPSG:32649","EPSG:4326",always_xy=True).transform

DECK="V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE"
RAMP="V54_LAKE00_EAST_WATER_CROSSING_SHORE_RAMP_INFERRED_ENDPOINT_MATCH"
S=[f"V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_0{i}_UNSURVEYED" for i in (1,2,3)]
ROAD_SEAM="V54_PAVEMENT_SEAM_CLOSE_ROAD_000__WALK_040_MODEL_EDGE_MATCH"
EVIDENCE=[
 {"url":"https://co.bnbu.edu.cn/en/info/1131/2702.htm","supports":"lakeside terraced hardscape and elevated building","limits":"no image-to-model registration"},
 {"url":"https://admission.bnbu.edu.cn/info/1732/1481.htm","supports":"wooden path meets planted building approach","limits":"type not coordinate"},
 {"url":"https://uic.edu.cn/info/1078/108739.htm","supports":"pedestrian boardwalk connects lake and planted bank","limits":"no approach elevation survey"},
 {"url":"https://www.bnbu.edu.cn/campus_life/Landscape_and_Facilities.htm","supports":"raised pedestrian connection, solid bank and glass building","limits":"no calibrated camera pose"},
 {"url":"https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/","supports":"pedestrian lanes, streets, courtyards in campus concept","limits":"masterplan not georeferenced as-built"},
]

def sha(b):return hashlib.sha256(b).hexdigest()
def unpack(data):
 assert data[:4]==b"glTF" and struct.unpack_from("<II",data,4)==(2,len(data))
 off=12;parts=[]
 while off<len(data):
  n,t=struct.unpack_from("<I4s",data,off);off+=8
  parts.append((t,data[off:off+n]));off+=n
 assert off==len(data) and [t for t,_ in parts]==[b"JSON",b"BIN\0"]
 return json.loads(parts[0][1]),parts[1][1]
def pack(doc,binary):
 j=json.dumps(doc,separators=(",",":"),ensure_ascii=False).encode()
 j+=b" "*(-len(j)%4);binary+=b"\0"*(-len(binary)%4)
 body=b"".join(struct.pack("<I4s",len(part),typ)+part for typ,part in ((b"JSON",j),(b"BIN\0",binary)))
 return b"glTF"+struct.pack("<II",2,12+len(body))+body

def build():
 base=BASE.read_bytes();raw=GIS.read_bytes();cfg=json.loads(CONTROL.read_text())
 assert cfg["source_glb_sha256"]==sha(base),"source GLB changed; re-audit controls"
 assert cfg["source_gis_sha256"]==sha(raw),"source GIS changed; re-audit controls"
 doc,original_binary=unpack(base)
 assert len(doc["meshes"])==1377
 gis=json.loads(raw);assert len(gis["features"])==522
 found={}
 for f in gis["features"]:
  name=f["properties"].get("render_model_node") or f["properties"].get("model_node")
  if name:found.setdefault(name,[]).append(transform(TO_UTM,shape(f["geometry"])))
 def polygon(name):
  assert name in found,name
  return max(found[name],key=lambda g:g.area)
 nodes={n.get("name"):n for n in doc["nodes"] if "mesh" in n}
 def height(name):
  p=doc["meshes"][nodes[name]["mesh"]]["primitives"][0]
  a=doc["accessors"][p["attributes"]["POSITION"]]
  v=doc["bufferViews"][a["bufferView"]]
  o=v["byteOffset"]+a.get("byteOffset",0);step=v.get("byteStride",12)
  zs=[struct.unpack_from("<f",original_binary,o+step*i+8)[0] for i in range(a["count"])]
  return min(zs),max(zs)
 water=polygon("LAKE_00")
 mat=len(doc["materials"])
 doc["materials"].append({"name":"V71_SOURCE_MATCHED_LAND_JOIN_NOT_SURVEYED",
   "doubleSided":True,"pbrMetallicRoughness":{"baseColorFactor":[.59,.61,.59,1],
     "metallicFactor":0,"roughnessFactor":1},"extensions":{"KHR_materials_unlit":{}}})
 if "KHR_materials_unlit" not in doc.setdefault("extensionsUsed",[]):
  doc["extensionsUsed"].append("KHR_materials_unlit")
 layer=next(n for n in doc["nodes"] if n.get("name")=="BNBU_GROUP_GROUND_CONNECTORS_UNSURVEYED")
 binary=original_binary
 patches=[];audit=[]
 def add_mesh(spec):
  nonlocal binary
  p=Polygon([(x+XY[0],y+XY[1]) for x,y in spec["local_polygon_xy"]])
  assert p.is_valid and 3<p.area<6
  a,b=polygon(spec["source_a"]),polygon(spec["source_b"])
  dist=a.distance(b)
  assert 2.3<dist<2.6 and abs(dist-spec["source_gap_m"])<.012
  assert p.distance(a)<.11 and p.distance(b)<.11
  assert p.intersection(water.buffer(.35)).area<1e-6
  h1,h2=height(spec["source_a"]),height(spec["source_b"])
  assert max(abs(h1[i]-h2[i]) for i in (0,1))<.005
  assert abs(h1[0]-spec["model_bottom_z"])<.005
  assert abs(h1[1]-spec["model_top_z"])<.005
  pts=[(x,y,z) for z in (spec["model_top_z"],spec["model_bottom_z"]) for x,y in spec["local_polygon_xy"]]
  vbuf=b"".join(struct.pack("<fff",*pt) for pt in pts)
  inds=[0,1,2,0,2,3,4,6,5,4,7,6]
  for i in range(4):
   j=(i+1)%4
   inds += [i,j,j+4,i,j+4,i+4]
  ibuf=b"".join(struct.pack("<H",v) for v in inds)
  vo=len(binary);binary+=vbuf;io=len(binary);binary+=ibuf
  vi=len(doc["bufferViews"])
  doc["bufferViews"] += [{"buffer":0,"byteOffset":vo,"byteLength":len(vbuf),"target":34962},
                         {"buffer":0,"byteOffset":io,"byteLength":len(ibuf),"target":34963}]
  ai=len(doc["accessors"])
  mins=[min(pt[i] for pt in pts) for i in range(3)]
  maxs=[max(pt[i] for pt in pts) for i in range(3)]
  doc["accessors"] += [
   {"bufferView":vi,"componentType":5126,"count":8,"type":"VEC3","min":mins,"max":maxs},
   {"bufferView":vi+1,"componentType":5123,"count":len(inds),"type":"SCALAR","min":[0],"max":[7]}
  ]
  mi=len(doc["meshes"])
  doc["meshes"].append({"name":spec["name"],"primitives":[{"attributes":{"POSITION":ai},
    "indices":ai+1,"material":mat}],"extras":{"is_surveyed":False,"metric_birdstrike_eligible":False}})
  ni=len(doc["nodes"])
  doc["nodes"].append({"name":spec["name"],"mesh":mi,
    "extras":{"role":"source_bound_at_grade_join","evidence":"model topology only, not surveyed"}})
  layer["children"].append(ni)
  doc["buffers"][0]["byteLength"]=len(binary)
  props={k:spec[k] for k in ("name","source_a","source_b","source_gap_m","model_bottom_z","model_top_z","evidence_tier")}
  props.update({"patch_area_model_m2":round(p.area,3),"is_surveyed":False,
                "metric_birdstrike_eligible":False,"water_overlap_m2":0})
  patches.append({"type":"Feature","geometry":mapping(transform(TO_WGS,p)),"properties":props})
 def record(a,b,status,note,existing=None):
  A,B=polygon(a),polygon(b)
  x,y=nearest_points(A,B)
  line=LineString([x,y]) if x.distance(y)>1e-5 else LineString([x,(x.x+.0001,x.y+.0001)])
  properties={"source_node_a":a,"source_node_b":b,"junction_status":status,
    "model_plan_gap_m":round(A.distance(B),4),"model_plan_overlap_m2":round(A.intersection(B).area,3),
    "model_lake_intersection_buffer_m2":round(line.buffer(.65).intersection(water).area,3),
    "source_z_top_a":round(height(a)[1],3),"source_z_top_b":round(height(b)[1],3),
    "model_top_offset_m":round(abs(height(a)[1]-height(b)[1]),3),
    "existing_model_bridge_or_join":existing,"note":note,
    "needs_photogrammetry":True,"accessibility_certified":False}
  audit.append({"type":"Feature","geometry":mapping(transform(TO_WGS,line)),"properties":properties})
 for item in cfg["features"]:
  add_mesh(item)
  record(item["source_a"],item["source_b"],"model_derived_pavement_join_added",
    "2.4-2.5m same-Z land-only inherited V61 gap; photo supports hardscape type, not position",item["name"])
 for a,b,status,note,existing in [
  (DECK,S[2],"vertical_mismatch_unresolved","deck z .91 vs promenade z .27; do not invent a ramp",None),
  (DECK,S[1],"vertical_mismatch_unresolved","deck/shore overlap but different z; cannot call walkable",None),
  (DECK,RAMP,"existing_east_bridge_ramp","V54 existing structure, not another new bridge",RAMP),
  (RAMP,"WALK_044","existing_east_landfall","V54 ramp overlaps original ground walk",RAMP),
  (S[1],"WALK_045","vertical_mismatch_unresolved","plan overlap but top elevation differs .24",None),
  ("ROAD_000","WALK_040","existing_road_to_path_seam","original v54 road-to-walk seam already connects",ROAD_SEAM),
  ("WALK_044","WALK_042","unresolved_land_gap","6m gap; no registered as-built route",None),
  ("WALK_042","WALK_040","unresolved_land_gap","11.5m gap; no registered as-built route",None),
  ("WALK_045","WALK_046","do_not_bridge_lake","15m separation touches modeled water; do not create road",None),
 ]:record(a,b,status,note,existing)
 level=[n for n in nodes if n.startswith("V52_LEVEL2_PEDESTRIAN_CONNECTION_")]
 assert len(level)==6 and all(height(n)[0]>3.4 for n in level)
 assert ROAD_SEAM in nodes and len(doc["meshes"])==1379 and len(audit)==11
 assert binary[:len(original_binary)]==original_binary
 original_doc,_=unpack(base)
 assert doc["meshes"][:1377]==original_doc["meshes"]
 assert doc["accessors"][:len(original_doc["accessors"])]==original_doc["accessors"]
 payload=pack(doc,binary)
 assert len(unpack(payload)[0]["meshes"])==1379
 D.mkdir(parents=True,exist_ok=True)
 OUT.write_bytes(payload)
 PATCH.write_text(json.dumps({"type":"FeatureCollection","features":patches,
   "meta":{"source_model_GIS_features":522,"new_patches_are_not_surveyed":True}},ensure_ascii=False,indent=2))
 GRAPH.write_text(json.dumps({"type":"FeatureCollection","features":audit,
   "meta":{"source":"v66/v69 inherited GIS & GLB, not ground truth",
     "plan_connections_do_not_certify_walkability":True}},ensure_ascii=False,indent=2))
 provenance={"version":"v71","source_glb_sha256":sha(base),"output_glb_sha256":sha(payload),
  "source_gis_sha256":sha(raw),"original_meshes":1377,"output_meshes":1379,
  "source_gis_features":522,"new_at_grade_seam_meshes":2,"audited_junctions":len(audit),
  "source_mesh_binary_sha256":sha(original_binary),
  "result_binary_original_prefix_sha256":sha(unpack(payload)[1][:len(original_binary)]),
  "source_control_file_sha256":sha(CONTROL.read_bytes()),"source_bounded_patches":patches,
  "existing_road_path_seam":ROAD_SEAM,"existing_east_lake_ramp":RAMP,
  "second_floor_walkways_are_not_road_bridges":level,"photo_reference_types_only":EVIDENCE,
  "limits":["no full camera registration","no authentic road widths","no surveyed ramps",
            "no new pond/lake footprint","not collision metric geometry"]}
 META.write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
 print(json.dumps({"original_meshes":1377,"result_meshes":1379,
    "new_seams":2,"audited_junctions":len(audit),"patch_m2":[p["properties"]["patch_area_model_m2"] for p in patches]},indent=2))
 return provenance

if __name__=="__main__":build()
