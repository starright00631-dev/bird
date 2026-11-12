"""Add 3D contour line segments to the independent ALOS-derived DSM reference.

No campus-model height registration is assumed. Existing DSM binary geometry
is preserved byte for byte; only the interpolated contours are appended.
"""
from __future__ import annotations
import hashlib, json, struct
from pathlib import Path
import numpy as np
from pyproj import Transformer

HERE=Path(__file__).resolve().parent
DATA=HERE/"generated"
INPUT=DATA/"BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb"
CONTOURS=DATA/"BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson"
OUTPUT=DATA/"BNBU_v73_ALOS_DSM_WITH_3D_CONTOURS.glb"
REPORT=DATA/"BNBU_v73_DSM_CONTOUR_PROVENANCE.json"
NAME="BNBU_v73_INTERPOLATED_10M_DSM_CONTOUR_LINES_NOT_SURVEYED"
EAST,NORTH,Z_LIFT=758940.,2474080.,0.5
COUNT=3737
TO_UTM=Transformer.from_crs("EPSG:4326","EPSG:32649",always_xy=True)

def unpack(raw):
    assert raw[:4]==b"glTF" and struct.unpack_from("<II",raw,4)==(2,len(raw))
    n,typ=struct.unpack_from("<I4s",raw,12)
    assert typ==b"JSON"
    doc=json.loads(raw[20:20+n])
    off=20+n;size,kind=struct.unpack_from("<I4s",raw,off)
    assert kind==b"BIN\x00"
    binary=raw[off+8:off+8+size]
    assert off+8+size==len(raw)
    return doc,binary

def pack(doc,binary):
    data=json.dumps(doc,ensure_ascii=False,separators=(",",":")).encode()
    data+=b" "*(-len(data)%4)
    binary+=b"\x00"*(-len(binary)%4)
    chunks=struct.pack("<I4s",len(data),b"JSON")+data
    chunks+=struct.pack("<I4s",len(binary),b"BIN\x00")+binary
    return b"glTF"+struct.pack("<II",2,len(chunks)+12)+chunks

def build():
    raw=INPUT.read_bytes()
    doc,orig_binary=unpack(raw)
    assert len(doc["meshes"])==len(doc["nodes"])==1
    assert doc["accessors"][0]["count"]==4140
    assert doc["accessors"][2]["count"]==24072
    assert doc["buffers"][0]["byteLength"]==len(orig_binary)
    assert len(doc["scenes"])==1 and doc["scenes"][0]["nodes"]==[0]
    contour_doc=json.loads(CONTOURS.read_text())
    features=contour_doc["features"]
    assert len(features)==COUNT
    assert all(f["geometry"]["type"]=="LineString" and len(f["geometry"]["coordinates"])==2 for f in features)
    heights=sorted({f["properties"]["elevation_m_interpolated"] for f in features})
    assert heights==list(range(10,111,10))
    assert all(f["properties"]["source"]=="ALOS_DERIVED_HGT" and f["properties"]["is_observed_contour"] is False for f in features)
    coords=[];colors=[]
    for f in features:
        h=float(f["properties"]["elevation_m_interpolated"])
        assert 0<=h<=120 and h%10==0
        for lon,lat in f["geometry"]["coordinates"]:
            assert 113.49<=lon<=113.54 and 22.33<=lat<=22.38
            east,north=TO_UTM.transform(lon,lat)
            coords.append((east-EAST,h+Z_LIFT,-(north-NORTH)))
            t=(h-10)/100
            colors.append((0.58+0.37*t,0.85-0.12*t,0.80-0.30*t))
    verts=np.asarray(coords,dtype="<f4")
    rgb=np.asarray(colors,dtype="<f4")
    assert verts.shape==rgb.shape==(COUNT*2,3)
    assert np.isfinite(verts).all()
    pos_offset=len(orig_binary)
    pos_bytes=verts.tobytes()
    col_offset=pos_offset+len(pos_bytes)
    color_bytes=rgb.tobytes()
    binary=orig_binary+pos_bytes+color_bytes
    assert binary[:len(orig_binary)]==orig_binary
    pos_view=len(doc["bufferViews"]);color_view=pos_view+1
    doc["bufferViews"] += [
        {"buffer":0,"byteOffset":pos_offset,"byteLength":len(pos_bytes),"target":34962},
        {"buffer":0,"byteOffset":col_offset,"byteLength":len(color_bytes),"target":34962},
    ]
    pos_accessor=len(doc["accessors"]);col_accessor=pos_accessor+1
    doc["accessors"] += [
        {"bufferView":pos_view,"componentType":5126,"count":len(verts),"type":"VEC3",
         "min":np.min(verts,axis=0).astype(float).tolist(),
         "max":np.max(verts,axis=0).astype(float).tolist()},
        {"bufferView":color_view,"componentType":5126,"count":len(rgb),"type":"VEC3"},
    ]
    mat=len(doc["materials"])
    doc["materials"].append({"name":"v73_contour_interpolated_display_only","doubleSided":True,
      "alphaMode":"BLEND","pbrMetallicRoughness":{
       "baseColorFactor":[1,1,1,0.85],"roughnessFactor":1,"metallicFactor":0}})
    mesh=len(doc["meshes"])
    doc["meshes"].append({"name":NAME,"primitives":[
        {"attributes":{"POSITION":pos_accessor,"COLOR_0":col_accessor},"mode":1,"material":mat}]})
    node=len(doc["nodes"])
    doc["nodes"].append({"name":NAME,"mesh":mesh,"extras":{
      "source":"v67 interpolated ALOS-derived DSM 10m isohypses",
      "surveyed":False,"vertical_registered_to_campus":False,
      "display_only":True,"vertical_draw_offset_m":Z_LIFT,
      "horizontal_crs":"EPSG:32649 local offsets 758940,2474080"}})
    doc["scenes"][0]["nodes"].append(node)
    doc["buffers"][0]["byteLength"]=len(binary)
    doc.setdefault("asset",{}).setdefault("extras",{})["v73_contours"]={
      "line_segments":COUNT,"display_lift_m":Z_LIFT,
      "cannot_replace_campus_shorelines_or_roads":True,
      "source_contours_are_interpolated_not_observed":True,
      "original_dsm_byte_prefix_sha256":hashlib.sha256(orig_binary).hexdigest()}
    OUTPUT.write_bytes(pack(doc,binary))
    after,after_bin=unpack(OUTPUT.read_bytes())
    assert after_bin[:len(orig_binary)]==orig_binary
    assert after["meshes"][0]==unpack(raw)[0]["meshes"][0]
    report={
      "version":"v73","model_scene":"independent ALOS-derived DSM, NOT calibrated campus terrain",
      "input_dsm_sha256":hashlib.sha256(raw).hexdigest(),
      "contour_geojson_sha256":hashlib.sha256(CONTOURS.read_bytes()).hexdigest(),
      "output_glb_sha256":hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
      "original_dsm_mesh_count":1,"output_dsm_mesh_count":2,
      "original_dsm_vertices":4140,"original_dsm_triangles":8024,
      "contour_segment_count":COUNT,"contour_vertex_count":COUNT*2,
      "contour_elevations_m":heights,"display_lift_m":Z_LIFT,
      "crs":"EPSG:32649, horizontal translation -758940 / -2474080",
      "elevation":"native DSM height + 0.50 m visual-only lift",
      "binary_source_unchanged":True,"is_surveyed":False,
      "registered_with_campus_buildings":False,
      "new_campus_buildings":0,"new_campus_roads":0,"new_campus_lakes":0,
      "source_url":"https://terrain.ardupilot.org/SRTM1/N22E113.hgt.zip",
      "interpretation":"10m contour lines are linear interpolations of ~30m DSM; not true 10m measurements"}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report

if __name__=="__main__":
    print(json.dumps(build(),indent=2))
