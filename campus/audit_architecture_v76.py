"""v76: recover architectural feature readability from immutable BNBU GLB.

Uses source-mesh dihedral/boundary edges, typed facade components and proximity
audits. No synthetic windows, balcony panels, roofs, paths or entrances.
"""
from __future__ import annotations
import collections, hashlib, json, math, re
from pathlib import Path
import numpy as np
from audit_connections_v74 import Surface, load_features, DATA, GLB, sha_file, OFFSET
from shapely.ops import nearest_points
from build_bridges_v75 import glb_pack, unpack_glb

ATLAS=DATA/"BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json"
LINES=DATA/"BNBU_v76_SOURCE_SHARP_FEATURE_EDGES_DISPLAY_ONLY.glb"
CATS=("T","V","D","LRC")
COLORS={"T":(.93,.74,.45),"V":(.85,.55,.35),"D":(.50,.78,.75),"LRC":(.98,.98,.91)}
SOURCES=[
  {"category":"T","url":"https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm",
    "role":"BNBU official T1 warm masonry, long recessed glazing, projecting floor-level edges",
    "limits":"Cannot assign a window count, pane width or facade orientation to each T1–T8 block"},
  {"category":"V","url":"https://www.bnbu.edu.cn/info/1076/6575.htm",
    "role":"Official 2014 Cultural Village description: residential common rooms and semi-open sky gardens",
    "limits":"V15–V29 sky garden bay and exact position not surveyed; do not copy phase-II balcony plans"},
  {"category":"V","url":"https://www.bnbu.edu.cn/info/1078/9214.htm",
    "role":"2017 school building-system description distinguishes T teaching from V residential buildings",
    "limits":"Historical building names and present-day hall names may differ"},
  {"category":"D","url":"https://bnbu.edu.cn/en/info/1255/10522.htm",
    "role":"Official Phase-II residence photos show balconies, open corridor railings and distinct exterior",
    "limits":"No image-to-D1…D6 calibrated viewpoint or balcony dimensions"},
  {"category":"D","url":"https://www.bnbu.edu.cn/en/info/1255/10406.htm",
    "role":"Official construction report: six residence halls with balcony accommodation typology",
    "limits":"Rendering and pre-occupation information are not as-built pane/door dimensions"},
  {"category":"LRC","url":"https://co.bnbu.edu.cn/",
    "role":"BNBU official Learning Resource Centre façade: white diagonal braces, blue glass, raised canopy and entrance",
    "limits":"Photo provides material and structural type, not measured LRC placement"},
  {"category":"LRC","url":"https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/",
    "role":"Design office confirms offset bridges, stairs and a lake-centered multilevel public space",
    "limits":"No surveyed threshold heights or precise faceted envelope"}
]
T_KEYS=[f"T{i}" for i in range(1,9)]
V_KEYS=[f"V{i}" for i in range(15,30)]
D_KEYS=[f"D{i}" for i in range(1,7)]
KEYS=T_KEYS+V_KEYS+D_KEYS+["LRC"]
def building_cat(key):
    if key.startswith("T"):return "T"
    if key.startswith("V"):return "V"
    if key.startswith("D"):return "D"
    return "LRC"

def root_node(key):
    if key in T_KEYS:return f"ROOF_DECK_{key}"
    if key in V_KEYS:return f"MAIN_{key}"
    if key in D_KEYS:return f"PHASEII_DORM_{key}"
    return "ROOF_DECK_LRC"

def component_group(name):
    # The V prefix in V34_/V40_ is a historical model *revision*, not a
    # residential V-series building. Match the *semantic suffix*, not version.
    if re.match(r"(?:^ROOF_(?:DECK|PARAPET)_T[1-8]$|^V40_MAIN_T[1-8]_FACADE_AND_SIDEWALLS$|^FLOOR_EDGE_NOT_GLASS_STORYBAND_T[1-8]_|^V25_P1_T[1-8]_LEVEL_|^V34_MODULE_V26_T[1-8]_)",name):
        return "T"
    if re.match(r"(?:^MAIN_V(?:1[5-9]|2[0-9])$|^ROOF_(?:DECK|PARAPET)_V(?:1[5-9]|2[0-9])$|^V63_RETOPOLOGIZED_OPAQUE_STORYEDGE_V(?:1[5-9]|2[0-9])_|^V25_P1_V25_LEVEL_)",name):
        return "V"
    if re.match(r"(?:^PHASEII_DORM_D[1-6]$|^V24_D[1-6]_|^V32_D[1-6]_|^PHASEII_V12_ROOF_DECK_PROXY_D[1-6]$)",name):
        return "D"
    if re.match(r"(?:^LRC_DIAGONAL_BRACE_|^LRC_STILT_|^LRC_SKYLIGHT_RIM$|^LRC_DOME_GLAZING_APPROX$|^ROOF_(?:DECK|PARAPET)_LRC$|^V26_LRC_|^V32_LRC_WATERFRONT_|^V40_MAIN_LRC_FACADE_AND_SIDEWALLS$|^V34_MODULE_V32_LRC_GLASS_)",name):
        return "LRC"
    return None

def belongs(name,key):
    if key in T_KEYS: return bool(re.search(r"(?:^|_)"+key+r"(?:_|$)",name))
    if key in V_KEYS: return bool(re.match(
      r"(?:^MAIN_|^ROOF_(?:DECK|PARAPET)_|^V63_RETOPOLOGIZED_OPAQUE_STORYEDGE_)",name)
      and re.search(r"(?:^|_)"+key+r"(?:_|$)",name))
    if key in D_KEYS: return bool(
        name==f"PHASEII_DORM_{key}" or name.startswith(f"V24_{key}_")
        or name.startswith(f"V32_{key}_") or name==f"PHASEII_V12_ROOF_DECK_PROXY_{key}"
        or name==f"V49_PHASEII_{key}_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE")
    return bool("LRC" in name and not
        any(s in name for s in ("LRC_SHORE_PROMENADE","lrc_lakeside_grass","LRC_LAKESIDE_SOURCE_MATCHED")))

def feature_edges(triangles,threshold_deg=34.0):
    """Non-invented sharp and open edges of actual inherited triangles."""
    normals=[];emap=collections.defaultdict(list)
    for face in triangles:
        xyz=face.astype(float)
        normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])
        length=np.linalg.norm(normal)
        if length<1.e-8:continue
        normal/=length
        idx=len(normals);normals.append(normal)
        for i,j in ((0,1),(1,2),(2,0)):
            a=tuple(np.round(xyz[i],4));b=tuple(np.round(xyz[j],4))
            if a==b:continue
            key=tuple(sorted((a,b)))
            emap[key].append(idx)
    out=[]
    threshold=math.cos(math.radians(threshold_deg))
    for edge,faces in sorted(emap.items()):
        if len(faces)==1 or min(float(np.dot(normals[faces[0]],normals[k])) for k in faces[1:])<threshold:
            out.extend(edge)
    return np.asarray(out,dtype="<f4").reshape(-1,3)

def sharp_line_glb(source,selected):
    arrays={};parts={}
    for cat in CATS:
        names=selected[cat]
        edges=[]
        for name in names:
            edge=feature_edges(source.triangles(name))
            if edge.size:edges.append(edge)
        ar=np.concatenate(edges,axis=0) if edges else np.empty((0,3),dtype="<f4")
        assert len(ar)>0 and len(ar)%2==0
        assert np.isfinite(ar).all()
        arrays[cat]=ar
        parts[cat]={"source_component_meshes":len(names),
                    "source_sharp_open_edge_segments":len(ar)//2,
                    "not_new_architectural_members":True}
    doc={"asset":{"version":"2.0","generator":"BNBU v76 source-edge topological preservation"},
      "scene":0,"scenes":[{"nodes":[]}],"nodes":[],"meshes":[],
      "materials":[],"bufferViews":[],"accessors":[]}
    chunks=[];offset=0
    for cat,ar in arrays.items():
        raw=ar.tobytes();chunks.append(raw)
        view=len(doc["bufferViews"]);idx=len(doc["accessors"])
        material=len(doc["materials"]);mesh=len(doc["meshes"]);node=len(doc["nodes"])
        color=COLORS[cat]
        doc["bufferViews"].append({"buffer":0,"byteOffset":offset,"byteLength":len(raw),"target":34962})
        doc["accessors"].append({"bufferView":view,"componentType":5126,
           "count":len(ar),"type":"VEC3","min":ar.min(axis=0).astype(float).tolist(),
           "max":ar.max(axis=0).astype(float).tolist()})
        doc["materials"].append({"name":f"v76_{cat}_existing_geometry_crease_edges",
          "doubleSided":True,"alphaMode":"BLEND",
          "pbrMetallicRoughness":{"baseColorFactor":[*color,.72],"metallicFactor":0,"roughnessFactor":1}})
        doc["meshes"].append({"name":f"BNBU_V76_SOURCE_EDGES_{cat}_NOT_SURVEYED",
          "primitives":[{"attributes":{"POSITION":idx},"mode":1,"material":material}],
          "extras":{"category":cat,"source_mesh_count":len(selected[cat]),
            "displayOnly":True,"no_extra_facade_area":True}})
        doc["nodes"].append({"name":f"BNBU_V76_SOURCE_EDGES_{cat}_NOT_SURVEYED","mesh":mesh,
          "extras":{"source_relative_z":True,"bird_collision_area_eligible":False}})
        doc["scenes"][0]["nodes"].append(node)
        offset+=len(raw)
    data=glb_pack(doc,b"".join(chunks))
    GLB_DOC,_=unpack_glb(data)
    assert len(GLB_DOC["meshes"])==4
    LINES.write_bytes(data)
    return parts

def proximity(source):
    geometry=load_features()
    paths=[(name,geom) for name,geom in geometry.items()
           if re.fullmatch(r"(?:WALK|ROAD)_\d{3}",name)]
    assert len(paths)==56
    # Phase-II PAVING_* radial routes and V49 ground links are source GLB
    # elements, absent from the 56 GIS WALK_/ROAD_ classes. Keep them as
    # unverified candidates, NEVER as certified traversable doors/paths.
    phaseii_names=sorted(n for n in source.nodes if
        re.fullmatch(r"PHASEII_V12_PAVING_phaseII_(?:radial_D[1-6]|inner_college_ring|west_road_concept)_surface",n)
        or re.fullmatch(r"V49_PHASEII_D[1-6]_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE",n))
    assert len(phaseii_names)==14
    phaseii=[(name,source.footprint(name)) for name in phaseii_names]
    candidates=paths+phaseii
    water=[(name,geom) for name,geom in geometry.items() if re.fullmatch(r"LAKE_\d{2}",name)]
    assert len(water)==5
    buildings=[]
    for key in KEYS:
        name=root_node(key)
        assert name in source.nodes,name
        footprint=source.footprint(name)
        triangles=source.triangles(name).reshape(-1,3)
        routes=sorted((float(footprint.distance(geom)),n) for n,geom in paths)
        route_candidates=sorted((float(footprint.distance(geom)),n) for n,geom in candidates)
        lakes=sorted((float(footprint.distance(geom)),n) for n,geom in water)
        components=sorted(n for n in source.nodes if belongs(n,key))
        buildings.append({"id":key,"family":building_cat(key),"source_anchor_node":name,
          "source_plan_geometry":"projection_of_inherited_roof_or_building_mass_not_field_footprint",
          "source_plan_area_sq_model_units":round(float(footprint.area),2),
          "source_bbox_utm_xy":[round(float(v),3) for v in footprint.bounds],
          "source_mesh_z_range":[round(float(triangles[:,2].min()),3),round(float(triangles[:,2].max()),3)],
          "existing_component_names":components,"existing_component_count":len(components),
          "nearest_walk_or_road":[{"node":n,"xy_gap_model_units":round(d,3)} for d,n in routes[:4]],
          "nearest_approach_candidates":[{"node":n,"xy_gap_model_units":round(d,3),
              "source_group":"phaseII_GLTF_inferred" if n in phaseii_names else "GIS_WALK_ROAD_inherited",
              "physical_connection_verified":False} for d,n in route_candidates[:4]],
          "nearest_lake":[{"node":n,"xy_gap_model_units":round(d,3)} for d,n in lakes[:2]],
          "no_measured_entry_doors":True,"no_photo_registered_windows":True,
          "not_proof_of_accessible_connection":True,
          "notes":"Planar proximity only. A source roof projection is not a known entrance; no accessibility or glass area claim."})
    assert len(buildings)==30
    network=[]
    center=source.footprint("PHASEII_V12_PAVING_phaseII_inner_college_ring_surface")
    for k in range(1,7):
        dorm=source.footprint(f"PHASEII_DORM_D{k}")
        radial_name=f"PHASEII_V12_PAVING_phaseII_radial_D{k}_surface"
        radial=source.footprint(radial_name)
        inferred=source.footprint(f"V49_PHASEII_D{k}_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE")
        p_d,p_r=nearest_points(dorm,radial)
        p_ring,p_r2=nearest_points(center,radial)
        dorm_min=float(np.min(source.triangles(f"PHASEII_DORM_D{k}")[:,:,2]))
        z_rad=source.local_top(radial_name,p_r)["z"]
        z_ring=source.local_top("PHASEII_V12_PAVING_phaseII_inner_college_ring_surface",p_ring)["z"]
        z_rad2=source.local_top(radial_name,p_r2)["z"]
        def local(point,z):
            return [round(point.x-OFFSET[0],4),round(point.y-OFFSET[1],4),round(z,4)]
        network.append({
            "dorm":f"D{k}",
            "dorm_to_radial_local_points":[local(p_d,dorm_min),local(p_r,z_rad)],
            "radial_to_ring_local_points":[local(p_r2,z_rad2),local(p_ring,z_ring)],
            "dorm_to_radial_plan_gap_model_units":round(float(dorm.distance(radial)),4),
            "radial_to_central_ring_gap_model_units":round(float(radial.distance(center)),4),
            "inferred_connector_to_radial_gap_model_units":round(float(inferred.distance(radial)),4),
            "inferred_connector_to_dorm_gap_model_units":round(float(inferred.distance(dorm)),4),
            "source_model_circulation_verified":False,
            "do_not_extrude_missing_paths":True})
    assert len(network)==6
    return buildings,network

def build():
    before=sha_file(GLB)
    source=Surface()
    selected={cat:sorted(n for n in source.nodes if component_group(n)==cat) for cat in CATS}
    assert all(len(selected[cat])>50 for cat in CATS),{k:len(v) for k,v in selected.items()}
    lines=sharp_line_glb(source,selected)
    buildings,phaseii_network=proximity(source)
    atlas={
      "version":"v76","source":"immutable inherited v71 GLB + v66 GIS",
      "source_glb_sha256":before,"original_meshes":1379,"original_gis_features":522,
      "families":{"T":{"source_building_count":8,"building_ids":T_KEYS},
        "V":{"source_building_count":15,"building_ids":V_KEYS},
        "D":{"source_building_count":6,"building_ids":D_KEYS},
        "LRC":{"source_building_count":1,"building_ids":["LRC"]}},
      "feature_edge_overlay":lines,"building_count":len(buildings),"building_records":buildings,
      "published_evidence":SOURCES,
      "algorithm":"source-surface crease/boundary extraction at 34 degrees, 0.0001 source-local vertex quantization",
      "spatial_environment":"30 buildings x (56 GIS WALK/ROAD + 14 Phase-II GLB radial/ring/grade candidates) and 5 lakes; source XY proximity is NEVER a verified door connection",
      "phaseII_route_candidate_count":14,
      "all_route_candidates_count":70,
      "phaseII_network_disconnection_audit":phaseii_network,
      "approach_glb_unchanged":True,
      "window_panel_count_measured":None,"dorm_balcony_number_measured":None,
      "lrc_fins_measured":None,"new_campus_triangles":0,
      "new_physical_windows_or_routes":0,"new_surveyed_glazing_area":0,
      "display_edge_lines_are_architecture_members":False,
      "critical_gaps":["T ribbons and storeys do not determine exact window grid",
        "V15–V29 not identical to Phase-II D1–D6 dormitory architecture",
        "LRC diagonal braces and oval skylight source-model shape not independently surveyed",
        "Source roof-to-WALK proximity is not a valid door or floor-level connection",
        "Six D dormitories are 18-21 model units from inherited radial paving and radial links are 40-48 from the central ring; source does not prove entrances",
        "Interbuilding elevated V52 span ends and v74 shoreline grade conflicts remain pending"],
      "future_validation":["Match 3+ distinct images per facade sector for COLMAP/pycolmap SfM",
        "Infer vanishing point axes and optimize image reprojection with source footprint anchors",
        "Do piecewise planar image/line constraints and test against withheld photograph",
        "Only after registration, add individually measured window openings and balconies",
        "Separate depiction-only materials from bird strike glass exposure denominator"]}
    assert sha_file(GLB)==before
    ATLAS.write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return atlas

if __name__=="__main__":
    a=build()
    print(json.dumps({"buildings":a["building_count"],
      "mesh_counts":{k:v["source_component_meshes"] for k,v in a["feature_edge_overlay"].items()},
      "source_edge_segments":{k:v["source_sharp_open_edge_segments"] for k,v in a["feature_edge_overlay"].items()}},indent=2))
