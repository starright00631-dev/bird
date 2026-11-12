"""Build BNBU v66 hierarchical scene and reconcile all *existing* GIS-to-mesh links.

No terrain heights, road alignments, building boundaries, glass planes or lake
contours are inferred. The 1377 inherited v64 mesh buffers remain byte-identical.
The v65 Y-up root rotation is retained.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import struct
from collections import Counter, defaultdict
from pathlib import Path

from build_v65 import display_glb, reconcile_geojson, source_bytes, unpack_glb

OUT = Path(__file__).resolve().parent / "generated"

LAYERS = {
    "terrain_unsurveyed": "Relative, modeled relief, not a DEM",
    "water_unsurveyed": "Inherited modeled lake surfaces, not a survey",
    "shore_unsurveyed": "Inherited sculpted shore relief, not measured",
    "vehicle_roads_unsurveyed": "Inherited vehicle road geometry; edges unmeasured",
    "pedestrian_paving_unsurveyed": "Existing model walkways and pavement",
    "ground_connectors_unsurveyed": "At-grade inferred links, explicitly NOT bridges",
    "elevated_boardwalk_unsurveyed": "Existing lake boardwalk mesh; height and alignment unregistered",
    "stairs_unsurveyed": "Inherited stair geometries, not measured",
    "glass_proxies_unregistered": "Photo-typology-based glazed surfaces; NOT calibrated glass panes",
    "architecture_opaque": "Inherited building and opaque structural meshes",
}

REPAIRED_STAIRS = {
    "V47_P1_T4_CONTINUOUS_16_TREAD_STAIR_3D_SOURCE_MODEL_INFERRED":
        "V49_P1_T4_16_TREAD_STAIR_MATCH_MODEL_FIRST_FLOOR_NOT_SURVEYED",
    "V47_P1_T6_CONTINUOUS_16_TREAD_STAIR_3D_SOURCE_MODEL_INFERRED":
        "V49_P1_T6_16_TREAD_STAIR_MATCH_MODEL_FIRST_FLOOR_NOT_SURVEYED",
    "V47_P1_T8_CONTINUOUS_16_TREAD_STAIR_3D_SOURCE_MODEL_INFERRED":
        "V49_P1_T8_16_TREAD_STAIR_MATCH_MODEL_FIRST_FLOOR_NOT_SURVEYED",
}
REPAIRED_GROUND = {
    "V48_PHASEII_D%d_GROUND_COURT_CONNECTOR_TOPOLOGICAL_INFERENCE_NOT_BRIDGE" % k:
        "V49_PHASEII_D%d_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE" % k
    for k in range(1, 7)
}


def classify_node(name: str) -> str:
    """Priority matters: an EASTLAKE BOARDWALK is NOT lake water;
    NOT_BRIDGE is an at-grade link; OPAQUE_TRANSOM is NOT glazing.
    """
    n = name.upper()
    if "TERRAIN_RELIEF" in n:
        return "terrain_unsurveyed"
    if "BOARDWALK" in n or "UNDERDECK" in n:
        return "elevated_boardwalk_unsurveyed"
    if "GRADE_MATCH_GROUND_LINK" in n or "GROUND_COURT_CONNECTOR" in n or \
            "CROSSING_SHORE_RAMP" in n:
        return "ground_connectors_unsurveyed"
    if n.startswith("LAKE_") or "WATER_SHORE_015" in n or \
            "WETLAND_RESTORED_WATER" in n or "WATER_TO_INHERITED_SHORE" in n:
        return "water_unsurveyed"
    if n.startswith("SHORE_") or "SHORE_BANK" in n or "WETLAND_SHORE" in n or \
            "LAKE_BANK" in n or "WETLAND_CURVED_SHORE" in n:
        return "shore_unsurveyed"
    if "ROAD_CONCEPT" in n:
        return "pedestrian_paving_unsurveyed"  # NOT a verified vehicle way
    if n.startswith("ROAD_") or "_ROAD_00" in n or "ROAD_000__" in n or \
            "ROAD_001" in n:
        return "vehicle_roads_unsurveyed"
    if "STAIR" in n or "TREAD" in n:
        return "stairs_unsurveyed"
    if n.startswith("WALK_") or "_WALK_" in n or "FOOTPATH" in n or \
            "PAVING" in n or "GROUND_COURT" in n:
        return "pedestrian_paving_unsurveyed"
    if "GLASS" in n or "GLAZ" in n:
        if "OPAQUE" not in n and "NON_GLASS" not in n and \
                ("GLASS" in n or "GLAZ" in n):
            return "glass_proxies_unregistered"
    return "architecture_opaque"


def pack_glb(document: dict, source_chunks: list) -> bytes:
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()
    encoded += b" " * ((-len(encoded)) % 4)
    chunks = [(b"JSON", encoded)] + source_chunks[1:]
    body = b"".join(struct.pack("<I4s", len(data), typ) + data for typ, data in chunks)
    output = b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body
    assert unpack_glb(output)[0] == document
    return output


def hierarchical_scene(v65: bytes) -> tuple[bytes, dict]:
    doc, chunks = unpack_glb(v65)
    assert doc["scenes"][0]["nodes"] == [0]
    root = doc["nodes"][0]
    original_children = list(root["children"])
    assert len(original_children) == 1377 and len(set(original_children)) == 1377
    assert len(doc["meshes"]) == 1377
    assert all(not doc["nodes"][idx].get("children") for idx in original_children)
    grouped = defaultdict(list)
    for idx in original_children:
        node = doc["nodes"][idx]
        assert "mesh" in node
        group = classify_node(node["name"])
        grouped[group].append(idx)
    assert set(grouped) == set(LAYERS) or set(grouped).issubset(LAYERS)
    new_children = []
    for group, description in LAYERS.items():
        if group not in grouped:
            continue
        idx = len(doc["nodes"])
        doc["nodes"].append({
            "name": "BNBU_GROUP_" + group.upper(),
            "children": grouped[group],
            "extras": {"evidence": description, "surveyed": False,
                       "layer": group, "metric_birdstrike_eligible": False},
        })
        new_children.append(idx)
    root["children"] = new_children
    doc.setdefault("asset", {}).setdefault("extras", {})["bnbu_v66"] = {
        "type": "hierarchy_and_references_only",
        "mesh_vertex_change": False,
        "mesh_count": 1377,
        "height_source": "relative, unregistered",
        "CTV_bungalow_included": False,
        "vehicle_road_source": "inherited model, not surveyed",
        "boardwalk_source": "existing model and photo typology, no georegistration",
    }
    result = pack_glb(doc, chunks)
    revised, revised_chunks = unpack_glb(result)
    assert revised_chunks[1:] == chunks[1:]
    assert revised["meshes"] == doc["meshes"]
    assert set(node["mesh"] for node in revised["nodes"] if "mesh" in node) == set(range(1377))
    assert all(n["name"] not in ("CTV_VILLA", "PRESIDENT_VILLA") for n in revised["nodes"])
    return result, {
        "mesh_count": 1377,
        "original_nodes": 1378,
        "hierarchy_nodes_added": len(new_children),
        "layer_counts": {k: len(grouped[k]) for k in LAYERS},
        "source_sha256": hashlib.sha256(v65).hexdigest(),
        "v66_sha256": hashlib.sha256(result).hexdigest(),
        "geometry_bytes_identical": True,
        "source_chunks_sha256": [hashlib.sha256(d).hexdigest() for _, d in chunks[1:]],
    }


def rebind_geojson(v65geo: bytes, v66glb: bytes) -> tuple[bytes, dict]:
    doc = json.loads(v65geo)
    scene, _ = unpack_glb(v66glb)
    names = {node.get("name") for node in scene["nodes"]}
    mapping = REPAIRED_STAIRS | REPAIRED_GROUND
    counts = Counter()
    unresolved = Counter()
    for feat in doc["features"]:
        p = feat["properties"]
        original = p.get("model_node")
        if original in mapping:
            assert p.get("render_model_node") is None, (original, p)
            target = mapping[original]
            assert target in names, target
            p["render_model_node"] = target
            p["v66_original_node"] = original
            p["v66_render_resolution"] = "replacement mesh verified by prior model correspondence"
            p["v66_edit_type"] = "association_only_no_new_geometry"
            counts["stair" if original in REPAIRED_STAIRS else "ground_connector"] += 1
        if original and not p.get("render_model_node"):
            unresolved[original] += 1
    assert counts == {"stair": 96, "ground_connector": 6}, counts
    assert not unresolved, unresolved
    assert len(doc["features"]) == 522
    assert sum(1 for f in doc["features"]
               if f["properties"].get("v65_unresolved_historical_node")) == 10
    doc["v66_association_provenance"] = {
        "source": "v64 GEOMETRY & GIS via v65 display repair",
        "new_geometry": False,
        "source_geometries_unchanged": True,
        "render_references_resolved": 112,
        "v65_lake_shore_references": 10,
        "v66_stair_references": 96,
        "v66_ground_connector_references": 6,
        "unresolved_model_nodes": 0,
        "warning": "Resolution against inherited scene does not verify its geometry on-site",
    }
    res = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    return res, {"stair_render_links_repaired": counts["stair"],
                 "at_grade_links_repaired": counts["ground_connector"],
                 "prior_water_shore_render_links": 10,
                 "unresolved_render_links": 0, "feature_count": 522,
                 "source_sha256": hashlib.sha256(v65geo).hexdigest(),
                 "output_sha256": hashlib.sha256(res).hexdigest()}


def build(out: Path = OUT) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    base_glb = source_bytes("BNBU_v64_ACTIVE.glb")
    base_gis = source_bytes("BNBU_v64_ACTIVE.geojson")
    v65glb, v65_summary = display_glb(base_glb)
    v65gis, _ = reconcile_geojson(base_gis, base_glb)
    v66glb, mesh_summary = hierarchical_scene(v65glb)
    v66gis, gis_summary = rebind_geojson(v65gis, v66glb)
    (out / "BNBU_v66_SEMANTIC_Y_UP.glb").write_bytes(v66glb)
    (out / "BNBU_v66_RESOLVED_REFERENCES.geojson").write_bytes(v66gis)
    metadata = {
        "version": "v66",
        "scope": "hierarchy, display classification, historical association repairs; no unregistered physical reconstruction",
        "geodetic_model_origin": {"utm49_easting_offset": 758940, "utm49_northing_offset": 2474080},
        "crs": {"source_model_xy": "EPSG:32649 local offset",
                "original_geojson": "EPSG:4326",
                "model_height": "relative, not DEM"},
        "v65": v65_summary,
        "scene": mesh_summary,
        "gis": gis_summary,
        "primary_reference_urls": [
            "https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg",
            "https://bnbu.edu.cn/campus_life/Campus_Map.htm",
            "https://www.4dmodel.com/UICcode/code/#/list",
            "https://bnbu.edu.cn/info/1075/115659.htm",
            "https://co.bnbu.edu.cn/en/info/1131/2702.htm",
        ],
        "limits": ["no DEM", "no orthorectified ground control",
                   "CTV outbuilding roof/location/name unverified",
                   "not a bird-strike glass exposure denominator"],
    }
    (out / "v66_provenance.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


if __name__ == "__main__":
    summary = build()
    print(json.dumps({"version": summary["version"],
                      "layers": summary["scene"]["layer_counts"],
                      "repaired": summary["gis"],
                      "mesh_bytes_unchanged": summary["scene"]["geometry_bytes_identical"]},
                     indent=2))
