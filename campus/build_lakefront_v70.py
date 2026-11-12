"""Reproducible evidence-linked *display* overlay for the BNBU lakefront.

Does not change existing site geometry. Source control for railing placement:
the V60 existing model boardwalk footprint intersected with LAKE_00. The
photo supports railings/deck *type*, but neither dimensions nor the GIS
footprint are surveyed. NEVER use overlay meshes for bird-strike exposure.
"""
from __future__ import annotations
import hashlib
import json
import math
import struct
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parent
GIS = ROOT / "generated/BNBU_v66_RESOLVED_REFERENCES.geojson"
MODEL = ROOT / "generated/BNBU_v69_WATERFRONT_REFINED.glb"
OUT = ROOT / "generated/BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json"
X_OFF, Y_OFF = 758940, 2474080
BOARD = "V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE"
STAIR = "V49_P1_T4_16_TREAD_STAIR_MATCH_MODEL_FIRST_FLOOR_NOT_SURVEYED"
EVIDENCE = [
    {"url":"https://co.bnbu.edu.cn/en/info/1131/2702.htm",
     "observed":"building on water edge, terraced promenades and bank planting",
     "use":"promenade versus vegetated shore visual classification only"},
    {"url":"https://hro.bnbu.edu.cn/index.htm",
     "observed":"curving raised walkway and vegetated banks in campus lake view",
     "use":"railing and planting-zone types, not mapped dimensions"},
    {"url":"https://uic.edu.cn/info/1078/108739.htm",
     "observed":"boardwalk crossing has posts and handrails beside landscaped ground",
     "use":"illustrative rail silhouette grounded on inherited V60 boardwalk"},
    {"url":"https://admission.bnbu.edu.cn/info/1732/1481.htm",
     "observed":"warm-toned wooden boardwalk, shrubs and built waterfront frontage",
     "use":"material type and existing ground-cover material selection only"},
]

def read_glb_info(path):
    b = path.read_bytes()
    assert b[:4] == b"glTF" and struct.unpack_from("<II", b, 4) == (2, len(b))
    jlen, jtyp = struct.unpack_from("<I4s", b, 12)
    assert jtyp == b"JSON"
    doc = json.loads(b[20:20+jlen])
    off = 20+jlen
    blen, typ = struct.unpack_from("<I4s", b, off)
    assert typ == b"BIN\x00"
    binary = b[off+8:off+8+blen]
    nodes = {n.get("name"):n for n in doc["nodes"] if "mesh" in n}
    assert len(doc["meshes"]) == 1377
    assert BOARD in nodes
    assert "V13_PHASEI_GREEN_CORRECTED_lrc_lakeside_grass" in nodes
    prim = doc["meshes"][nodes[BOARD]["mesh"]]["primitives"][0]
    acc = doc["accessors"][prim["attributes"]["POSITION"]]
    view = doc["bufferViews"][acc["bufferView"]]
    offset = view["byteOffset"] + acc.get("byteOffset",0)
    assert acc["componentType"] == 5126 and acc["type"] == "VEC3"
    z = [struct.unpack_from("<f",binary,offset+i*12+8)[0] for i in range(acc["count"])]
    assert 0.5 < max(z) < 1.5
    return max(z),hashlib.sha256(b).hexdigest(),nodes

def one_feature(data, name, role=None):
    matches = [f for f in data["features"]
               if f["properties"].get("model_node") == name
               and (role is None or f["properties"].get("role") == role)]
    assert len(matches)==1, (name,role,len(matches))
    return matches[0]

def build():
    data = json.loads(GIS.read_text(encoding="utf-8"))
    assert len(data["features"]) == 522
    projector = Transformer.from_crs("EPSG:4326","EPSG:32649",always_xy=True).transform
    deck = transform(projector,shape(one_feature(data,BOARD)["geometry"]))
    lake = transform(projector,shape(one_feature(data,"LAKE_00","water_existing_v44_not_surveyed")["geometry"]))
    stair_features=[f for f in data["features"] if f["properties"].get("render_model_node")==STAIR]
    # Existing GIS contains stair body plus individual tread/edge records.
    # Use the primary, largest 2D body polygon rather than repeated tread views.
    assert len(stair_features)>=16
    stair=max((transform(projector,shape(f["geometry"])) for f in stair_features),key=lambda g:g.area)
    assert deck.is_valid and lake.is_valid and stair.is_valid
    assert 485 < deck.area < 492 and 9500 < lake.area < 9700
    overlap = deck.intersection(lake).area
    assert 402 < overlap < 415
    source_deck_z,model_hash,nodes = read_glb_info(MODEL)
    eligible = deck.exterior.intersection(lake.buffer(-.8))
    lines = [eligible] if eligible.geom_type == "LineString" else list(eligible.geoms)
    lines = [line for line in lines if line.geom_type=="LineString" and line.length>15]
    assert len(lines) >= 1 and sum(l.length for l in lines)>210
    polylines=[]
    for line in lines:
        sample_count = math.ceil(line.length/.68)
        points=[]
        for i in range(sample_count+1):
            p=line.interpolate(i/sample_count,normalized=True)
            points.append([round(p.x-X_OFF,4),round(p.y-Y_OFF,4),round(source_deck_z,4)])
        polylines.append(points)
    # One source-linked overlay only. Each point lies on the model deck footprint,
    # not a new guessed bridge axis.
    detail={
        "version":"v70",
        "source":"model-internal deck footprint; photo-supported *typology*, not survey",
        "role":"DISPLAY_ONLY_NO_METRIC_GEOMETRY",
        "crs":"local original GLB: x=EPSG32649 easting-758940, y=northing-2474080, z=relative height",
        "source_glb_sha256":model_hash,
        "source_gis_sha256":hashlib.sha256(GIS.read_bytes()).hexdigest(),
        "existing_deck_node":BOARD,
        "water_node":"LAKE_00",
        "original_meshes":1377,
        "original_gis_features":522,
        "deck_polygon_area_m2_model_only":round(deck.area,2),
        "over_lake_area_m2_model_only":round(overlap,2),
        "rail_m_path_model_only":round(sum(l.length for l in lines),2),
        "visual_rail_height_above_existing_deck_m":.9,
        "visual_post_spacing_m":2.8,
        "railing_xy_polylines_local":polylines,
        "surface_materials":{"boardwalk":"photo type: warm timber-tone finish, boards not measured",
                             "existing_lrc_grass":"existing V13 designated lawn, no new land parcel",
                             "existing_lrc_prom": "existing V61 slabs, photo type: light concrete"},
        "validation_flags":[{
            "node":STAIR,
            "issue":"plan-view footprint overlaps inherited lake; can be elevated or model-misaligned",
            "model_plan_overlap_m2":round(stair.intersection(lake).area,2),
            "action":"DO NOT delete, move or resolve without camera/height registration",
            "severity":"needs-spatial-verification"}],
        "photo_evidence":EVIDENCE,
        "rules":["do not create additional ponds","do not replace waterline geometry",
                 "do not claim rail dimensions measured",
                 "keep display proxy separate from collision/risk geometry"],
    }
    assert 47 < detail["validation_flags"][0]["model_plan_overlap_m2"] < 50
    assert len(polylines[0]) > 100
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(detail,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"model_deck_area":detail["deck_polygon_area_m2_model_only"],
                      "over_water":detail["over_lake_area_m2_model_only"],
                      "railing_source_boundary_length":detail["rail_m_path_model_only"],
                      "points":sum(map(len,polylines)),
                      "flagged_stair_plan_overlap":detail["validation_flags"][0]["model_plan_overlap_m2"]},indent=2))
    return detail

if __name__=="__main__":
    build()
