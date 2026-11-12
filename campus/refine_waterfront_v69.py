"""Evidence-aware waterfront visual material refinement, not a shoreline survey.

Source: v66 exact GLB; preserve 1377 meshes, all positions, all indices,
all scene transforms, lake boundaries and the original GIS. Only existing
per-vertex shoreline color data and PBR material references are updated.
Photos support *typologies*; not spatially registered material measurements.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"generated/BNBU_v66_SEMANTIC_Y_UP.glb"
OUTPUT=ROOT/"generated/BNBU_v69_WATERFRONT_REFINED.glb"
MANIFEST=ROOT/"generated/BNBU_v69_WATERFRONT_PROVENANCE.json"
REFERENCES=[
    "https://www.bnbu.edu.cn/en/info/1077/3242.htm",
    "https://www.bnbu.edu.cn/info/1077/4589.htm",
    "https://co.bnbu.edu.cn/en/info/1131/2702.htm",
    "https://www.uic.edu.cn/en/info/1055/8428.htm",
]

def decode_glb(blob):
    assert blob[:4]==b"glTF" and struct.unpack_from("<II",blob,4)==(2,len(blob))
    off=12;chunks=[]
    while off<len(blob):
        size,kind=struct.unpack_from("<I4s",blob,off);off+=8
        chunks.append((kind,blob[off:off+size]));off+=size
    assert off==len(blob) and len(chunks)==2
    assert [x[0] for x in chunks]==[b"JSON",b"BIN\0"]
    return json.loads(chunks[0][1]),chunks[1][1]

def encode_glb(doc,data):
    payload=json.dumps(doc,ensure_ascii=False,separators=(",",":")).encode()
    payload+=b" "*((-len(payload))%4)
    data+=b"\0"*((-len(data))%4)
    chunks=b"".join(struct.pack("<I4s",len(x),kind)+x for kind,x in (
        (b"JSON",payload),(b"BIN\0",data)))
    return b"glTF"+struct.pack("<II",2,12+len(chunks))+chunks

def geometry_digest(doc,bin):
    h=hashlib.sha256()
    for mesh in doc["meshes"]:
        for part in mesh["primitives"]:
            for aid in (part["attributes"]["POSITION"],part["indices"]):
                acc=doc["accessors"][aid]
                view=doc["bufferViews"][acc["bufferView"]]
                beg=view["byteOffset"]
                h.update(bin[beg:beg+view["byteLength"]])
    return h.hexdigest()

def mix(a,b,t):
    t=min(1.0,max(0.0,t));t=t*t*(3-2*t)
    return tuple(round(x+(y-x)*t) for x,y in zip(a,b))

def shore_color(z,wetland=False):
    if wetland:
        if z<-.045:return (75,102,87)
        if z<.015:return mix((75,102,87),(99,123,96),(z+.045)/.06)
        return mix((99,123,96),(121,153,108),(z-.015)/.05)
    if z<-.06:return (75,105,99)
    if z<.025:return mix((75,105,99),(120,132,109),(z+.06)/.085)
    if z<.17:return mix((120,132,109),(130,148,106),(z-.025)/.145)
    return mix((130,148,106),(150,174,125),(z-.17)/.27)

def build(source):
    doc,data0=decode_glb(source)
    assert len(doc["meshes"])==1377
    before=geometry_digest(doc,data0)
    data=bytearray(data0)
    nodes={n["name"]:n for n in doc["nodes"] if n.get("name") and "mesh" in n}
    for name in ["LAKE_%02d"%i for i in range(5)]+["SHORE_%02d"%i for i in range(5)]:
        assert name in nodes, name
    water_pond="V55_P2_ARCHIVED_WETLAND_RESTORED_WATER_NOT_SURVEYED"
    wetland_bank="V55_P2_ARCHIVED_WETLAND_CONTINUOUS_3D_BANK_NOT_DEM"
    wetland_ground="V55_P2_WETLAND_OUTER_VEGETATED_GROUND_NOT_RANDOM_TREES"
    for name in (water_pond,wetland_bank,wetland_ground):assert name in nodes
    materials=doc.setdefault("materials",[])
    def add(name,color,metal,rough,clear=0):
        material={"name":name,"doubleSided":True,
            "pbrMetallicRoughness":{"baseColorFactor":[*color,1.0],
                "metallicFactor":metal,"roughnessFactor":rough}}
        if clear:
            material["extensions"]={"KHR_materials_clearcoat":{
                "clearcoatFactor":clear,"clearcoatRoughnessFactor":0.15}}
        materials.append(material)
        return len(materials)-1
    water=add("v69_water_reflectance_not_measured",(.41,.66,.67),.018,.32,.43)
    pond=add("v69_archived_wetland_different_water_typology",(.34,.50,.42),.012,.50,.25)
    bank=add("v69_source_profile_dry_wet_shore",(1,1,1),0,.94)
    marsh=add("v69_wetland_bank_model_relative",(1,1,1),0,1)
    seam=add("v69_lake_shore_existing_seam",(.52,.61,.52),.012,.86)
    counts={"existing_water":0,"existing_shore":0,"seam":0,"wetland_water":0,
            "wetland_bank":0,"wetland_ground":0,"recolored_vertices":0}
    def prim(name):
        mesh=doc["meshes"][nodes[name]["mesh"]]
        assert len(mesh["primitives"])==1
        return mesh["primitives"][0]
    def setmat(name,material):prim(name)["material"]=material
    def color(name,wet=False):
        p=prim(name)
        ca=doc["accessors"][p["attributes"]["COLOR_0"]]
        pa=doc["accessors"][p["attributes"]["POSITION"]]
        cv=doc["bufferViews"][ca["bufferView"]]
        pv=doc["bufferViews"][pa["bufferView"]]
        assert ca["componentType"]==5121 and ca["type"]=="VEC4"
        assert pa["componentType"]==5126 and pa["type"]=="VEC3"
        assert ca["count"]==pa["count"]
        co=cv["byteOffset"]+ca.get("byteOffset",0)
        po=pv["byteOffset"]+pa.get("byteOffset",0)
        for v in range(pa["count"]):
            z=struct.unpack_from("<f",data,po+12*v+8)[0]
            data[co+4*v:co+4*v+4]=bytes((*shore_color(z,wet),255))
        counts["recolored_vertices"]+=pa["count"]
    for i in range(5):
        name="LAKE_%02d"%i
        setmat(name,water);counts["existing_water"]+=1
        name="SHORE_%02d"%i
        setmat(name,bank);color(name);counts["existing_shore"]+=1
    for name in nodes:
        if name.startswith("V50_LAKE_") and "_WATER_SHORE_" in name:
            setmat(name,seam);counts["seam"]+=1
    setmat(water_pond,pond);counts["wetland_water"]+=1
    for name,role in ((wetland_bank,"wetland_bank"),(wetland_ground,"wetland_ground")):
        setmat(name,marsh);color(name,True);counts[role]+=1
    assert counts["seam"]==5 and counts["recolored_vertices"]==95984
    if "KHR_materials_clearcoat" not in doc.setdefault("extensionsUsed",[]):
        doc["extensionsUsed"].append("KHR_materials_clearcoat")
    doc["asset"].setdefault("extras",{})["v69_waterfront"]={
        "geometry_unchanged":True,"shoreline_surveyed":False,
        "treatment":"appearance only, height-toned inherited bank vertices, not measured materials",
        "source_evidence_urls":REFERENCES}
    assert geometry_digest(doc,data)==before
    out=encode_glb(doc,bytes(data))
    final,_=decode_glb(out)
    assert final["nodes"]==decode_glb(source)[0]["nodes"]
    assert final["accessors"]==decode_glb(source)[0]["accessors"]
    assert len(final["meshes"])==1377
    result={"version":"v69","source":"v66","mesh_count":1377,
        "geometry_position_and_index_digest":before,
        "position_index_geometry_unchanged":True,
        "source_sha256":hashlib.sha256(source).hexdigest(),
        "output_sha256":hashlib.sha256(out).hexdigest(),
        "edited":counts,
        "photos_for_typology_not_camera_registration":REFERENCES,
        "source_constraints":{"west_and_east_lakes":"five inherited surface entities, not five separately verified real lakes",
            "east_hill_ponds":"Official 2019 report documents two freshwater ponds and a seasonal wetland, but coordinates and waterline are not available",
            "archived_phase_ii_wetland":"Model-only, NOT identified with the officially described east hill ponds"},
        "prohibited":{"new_surveyed_waterline":True,"invented_pond_mesh":True,"DEM_vertical_blend":True}}
    return out,result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--out",type=Path,default=OUTPUT)
    parser.add_argument("--manifest",type=Path,default=MANIFEST)
    args=parser.parse_args()
    model,report=build(args.source.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(model)
    args.manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"meshes":report["mesh_count"],"changed":report["edited"],
       "geometry_unchanged":report["position_index_geometry_unchanged"]},indent=2))
