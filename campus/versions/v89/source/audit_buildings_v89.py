#!/usr/bin/env python3
"""Read-only building inventory and geometry audit for BNBU v88."""
import argparse, hashlib, json, re
from pathlib import Path
from collections import Counter
import numpy as np
import trimesh

CORE_IDS = [*[f"T{i}" for i in range(1, 9)], *[f"V{i}" for i in range(15, 30)], *[f"D{i}" for i in range(1, 7)], "LRC"]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def category(name):
    u = name.upper()
    if "STORYEDGE" in u or "FLOOR_EDGE" in u or "NOT_GLASS" in u:
        return "story_edges"
    if any(x in u for x in ("OPAQUE", "END_JAMB", "FLOORLINE", "TRANSOM", "MULLION", "HEAD_", "SILL_")) and ("GLASS" in u or "GLAZ" in u):
        return "opaque_frame_or_return"
    if "GLASS" in u or "GLAZING" in u:
        return "glazing"
    if "STAIR" in u or "TREAD" in u:
        return "stairs"
    if any(x in u for x in ("CROSSRIB", "BRACE", "PILLAR", "PIER", "COLUMN", "STILT")):
        return "supports_and_bracing"
    if "GALLERY" in u or "SPANDREL" in u:
        return "gallery_and_spandrel"
    if any(x in u for x in ("ROOF_DECK", "ROOF_FIELD", "ROOF_PARAPET")):
        return "roof"
    if name.startswith(("MAIN_", "V40_MAIN_", "PHASEII_DORM_")):
        return "primary_mass_or_facade"
    if "BALCONY" in u or "RAIL" in u:
        return "balcony_and_rails"
    return "other"

def mesh_stats(scene, node):
    transform, key = scene.graph[node]
    mesh = scene.geometry[key]
    v = trimesh.transform_points(np.asarray(mesh.vertices), transform)
    return {
        "node": node, "vertices": int(len(mesh.vertices)), "triangles": int(len(mesh.faces)),
        "connected_components": int(len(mesh.split(only_watertight=False))),
        "watertight": bool(mesh.is_watertight),
        "world_bounds_xyz": np.round(np.vstack([v.min(0), v.max(0)]), 4).tolist(),
        "z_levels_rounded_0_01": np.unique(np.round(v[:, 2], 2)).astype(float).tolist()
    }

def audit_record(r, scene, group):
    names = list(r.get("existing_component_names", []))
    missing = [n for n in names if n not in scene.graph.nodes_geometry]
    if missing:
        raise AssertionError(f"{r['id']} missing scene nodes: {missing[:10]}")
    cats = Counter(category(n) for n in names)
    triangles = Counter()
    for n in names:
        _, key = scene.graph[n]
        triangles[category(n)] += len(scene.geometry[key].faces)
    primary = [n for n in names if category(n) == "primary_mass_or_facade"]
    story = [n for n in names if category(n) == "story_edges"]
    glass = [n for n in names if category(n) == "glazing"]
    frames = [n for n in names if category(n) == "opaque_frame_or_return"]
    stairs = [n for n in names if category(n) == "stairs"]
    rails = [n for n in names if category(n) == "balcony_and_rails"]
    ribs = [n for n in names if "CROSSRIB" in n.upper()]
    return {
        "id": r["id"], "record_group": group, "family": r.get("family", "OTHER"),
        "official_name": r.get("official_name"), "display_label": r.get("display_label"),
        "identity_source_url": r.get("identity_source_url"),
        "source_anchor_node": r.get("source_anchor_node"),
        "anchor_is_surveyed_footprint": False,
        "component_count": len(names), "component_category_counts": dict(cats),
        "component_category_triangles": dict(triangles),
        "primary_mesh_nodes": [mesh_stats(scene, n) for n in primary],
        "story_edge_nodes": story, "glazing_surface_nodes": glass,
        "opaque_frame_or_return_nodes": frames, "balcony_or_rail_nodes": rails,
        "stair_nodes": stairs, "roof_crossrib_nodes": ribs,
        "is_surveyed": bool(r.get("is_surveyed", False)),
        "is_building_footprint": bool(r.get("is_building_footprint", False)),
        "is_routable": bool(r.get("is_routable", False)),
        "birdstrike_area_eligible": bool(r.get("birdstrike_area_eligible", False)),
        "status": "INVENTORY_AUDITED_FEATURE_COMPLETENESS_NOT_CERTIFIED"
    }

def build(package):
    glb = package / "generated/BNBU_v71_CONNECTED_LAKEFRONT.glb"
    atlas_p = package / "generated/BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json"
    registry_p = package / "registry/BNBU_v88_BUILDING_ASSET_REGISTRY.json"
    before = sha256(glb)
    atlas, registry = json.loads(atlas_p.read_text()), json.loads(registry_p.read_text())
    scene = trimesh.load(glb, force="scene", process=False)
    reg = {x["id"]: x for x in registry.get("mapped_assets", [])}
    by_id = {x["id"]: x for x in atlas["building_records"]}
    if set(by_id) != set(CORE_IDS):
        raise AssertionError("Core building inventory mismatch")
    core = [audit_record({**by_id[k], **reg.get(k, {})}, scene, "core_30") for k in CORE_IDS]
    ext = [audit_record({**x, **reg.get(x["id"], {})}, scene, "extended_mapped_8") for x in atlas.get("extended_records", [])]
    v = [x for x in core if x["family"] == "V"]
    t = [x for x in core if x["family"] == "T"]
    d = [x for x in core if x["family"] == "D"]
    v_with = [x["id"] for x in v if x["story_edge_nodes"]]
    v_without = [x["id"] for x in v if not x["story_edge_nodes"]]
    t_glass = {x["id"]: len(x["glazing_surface_nodes"]) for x in t}
    t_frames = {x["id"]: len(x["opaque_frame_or_return_nodes"]) for x in t}
    v25 = next(x for x in core if x["id"] == "V25")
    v25m = next(x for x in v25["primary_mesh_nodes"] if x["node"] == "MAIN_V25")
    flags = [
      {"id":"V25_LOW_RESOLUTION_PRIMARY_MASS","severity":"HIGH","classification":"MODEL_RESOLUTION_OUTLIER; REAL-WORLD DETAIL REQUIRES PHOTO REGISTRATION","affected":["V25"],"evidence":{"vertices":v25m["vertices"],"triangles":v25m["triangles"],"z_levels":v25m["z_levels_rounded_0_01"]},"finding":"V25 has a 62-vertex / 120-triangle primary mass with only base and roof Z levels and no separate story-edge nodes."},
      {"id":"V_SERIES_FACADE_FEATURE_TYPE_GAP","severity":"HIGH","classification":"OFFICIAL_PHOTO_SUPPORTED_FEATURE_TYPE; INDIVIDUAL_ASSIGNMENT_UNRESOLVED","affected":[x["id"] for x in v],"evidence":{"glazing":{x["id"]:len(x["glazing_surface_nodes"]) for x in v},"balcony_rails":{x["id"]:len(x["balcony_or_rail_nodes"]) for x in v},"photo":"https://admission.bnbu.edu.cn/info/1734/1470.htm"},"finding":"No V15-V29 record has separately named glazing, balcony or railing components, while the official Phase-I dormitory exterior shows window bays, recessed balcony-like bays and guardrails. The photo is not registered to individual V buildings."},
      {"id":"V_SERIES_STORY_EDGE_COVERAGE_ASYMMETRY","severity":"HIGH_REVIEW","classification":"INVENTORY_ASYMMETRY_NOT_CONFIRMED_PHYSICAL_OMISSION","affected":v_without,"comparison_group":v_with,"finding":"Only 8 of 15 V buildings have separate V63 story-edge nodes; the other seven need face-level checks."},
      {"id":"T1_PHOTO_BACKED_GLAZING_OMISSION","severity":"HIGH","classification":"OFFICIAL_PHOTO_VS_COMPONENT_INVENTORY_MISMATCH","affected":["T1"],"evidence":{"explicit_glazing_nodes":len(next(x for x in t if x["id"]=="T1")["glazing_surface_nodes"]),"photo":"https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm"},"finding":"The official T1 page identifies the address as T1-602 and shows horizontal ribbon glazing and lower-level glazing; the current T1 inventory has zero separately identified transparent glazing surfaces."},
      {"id":"T_SERIES_GLAZING_COVERAGE_ASYMMETRY","severity":"HIGH_REVIEW","classification":"EVIDENCE_GAP_AND_COMPONENT_COVERAGE_ASYMMETRY","affected":[k for k,vv in t_glass.items() if vv==0],"evidence":{"transparent_surfaces":t_glass,"opaque_frames_returns":t_frames},"finding":"T2/T3/T4 have 7/3/4 transparent glazing surfaces; T1/T5-T8 have none. Opaque mullions, jambs and returns are counted separately."},
      {"id":"D_SERIES_FACADE_FEATURE_MAPPING_GAP","severity":"HIGH_REVIEW","classification":"OFFICIAL_PHOTO_FEATURE_TYPE; D1-D6_ASSIGNMENT_UNRESOLVED","affected":[x["id"] for x in d],"evidence":{"per_building":{"id":{x["id"]:x["component_category_counts"] for x in d}},"photo":"https://admission.bnbu.edu.cn/info/1734/1469.htm"},"finding":"D1-D6 have no separately named glazing, balcony/rail or stair nodes; official Phase-II dormitory imagery shows deep recessed facade grids, window/balcony bays and open guardrails, but is not registered to an individual D block."}
    ]
    for asset in registry.get("unmapped_official_assets", []):
        flags.append({"id":"P2_LRC_LAB_COMPLEX_UNMAPPED","severity":"CRITICAL","classification":"OFFICIAL_BUILDING_WITHOUT_VERIFIED_MESH_MAPPING","affected":[asset["id"]],"evidence":asset,"finding":"The official Phase-II LRC/Laboratory Complex is not mapped in the physical master and must not be confused with the circular commons proxy."})
    flags.append({"id":"LRC_SKYLIGHT_CANDIDATE_SEPARATE","severity":"MEDIUM","classification":"OPTIONAL_UNSURVEYED_CANDIDATE_NOT_IN_DEFAULT_MASTER","affected":["LRC"],"finding":"The 17,410-vertex / 34,816-triangle skylight shell remains a separate unsurveyed candidate, not part of the default master."})
    result = {
      "version":"v89-audit-only","source_package":"BNBU_Campus_Full_v88",
      "source_glb_sha256":before,"source_atlas_sha256":sha256(atlas_p),"source_registry_sha256":sha256(registry_p),
      "active_scene_mesh_nodes":len(scene.graph.nodes_geometry),"core_buildings":core,"extended_assets":ext,
      "unmapped_official_assets":registry.get("unmapped_official_assets",[]),
      "quarantined_hypotheses":registry.get("quarantined_hypotheses",[]),
      "defect_flags":flags,
      "photo_evidence_register":[
        {"id":"T1_OFFICIAL_FACADE","url":"https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm","observations":["horizontal ribbon glazing","lower-level glazing","projecting white frames","warm brick/cladding"],"registration":"feature presence only"},
        {"id":"PHASE_I_DORMITORY_EXTERIOR","url":"https://admission.bnbu.edu.cn/info/1734/1470.htm","observations":["window bays","recessed balcony-like bays","guardrails"],"registration":"typology only; individual V assignment unresolved"},
        {"id":"PHASE_II_DORMITORY_EXTERIOR","url":"https://admission.bnbu.edu.cn/info/1734/1469.htm","observations":["deep recessed facade grid","window/balcony bays","open guardrails"],"registration":"typology only; individual D assignment unresolved"},
        {"id":"PHASE_II_LRC_LAB_COMPLEX","url":"https://www.bnbu.edu.cn/en/info/1076/12578.htm","design_reference":"https://www.aedas.com/en/project/learning-resources-center-at-beijing-normal-hong-kong-baptist-university-bnbu-no-2-campus/","observations":["cubic massing","vertical fins","central glazed atrium","cantilevered/recessed volumes","sky garden"],"registration":"project imagery, not as-built survey"}
      ],
      "scope_limits":["Inventory statistics do not certify real-world completeness.","Roof-anchor projections are not surveyed footprints, doors, windows or bird-strike glass area.","No geometry, GIS, material or viewer files were modified."]
    }
    if sha256(glb) != before:
        raise AssertionError("Source GLB changed during audit")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--package-root",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    result=build(a.package_root.resolve())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\\n","utf-8")
    print(json.dumps({"pass":True,"core":len(result["core_buildings"]),"extended":len(result["extended_assets"]),"active_mesh_nodes":result["active_scene_mesh_nodes"],"flags":[x["id"] for x in result["defect_flags"]]},ensure_ascii=False))
if __name__=="__main__":
    main()
