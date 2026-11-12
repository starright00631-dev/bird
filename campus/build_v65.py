"""Build a geometry-preserving, Y-up display GLB and reconciled evidence overlay.

v64 has X=easting, Y=northing, Z=model-relative height. glTF viewers
expect Y-up. Never change mesh vertices/indices or claim surveyed accuracy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import lzma
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "generated"
Y_UP = [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]


def source_bytes(name: str) -> bytes:
    raw = ASSETS / name
    return raw.read_bytes() if raw.exists() else lzma.decompress((ASSETS / (name + ".xz")).read_bytes())


def unpack_glb(data: bytes):
    assert data[:4] == b"glTF" and struct.unpack_from("<I", data, 4)[0] == 2
    assert struct.unpack_from("<I", data, 8)[0] == len(data)
    offset, chunks = 12, []
    while offset < len(data):
        n, typ = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunks.append((typ, data[offset:offset + n]))
        offset += n
    assert offset == len(data) and chunks[0][0] == b"JSON"
    return json.loads(chunks[0][1]), chunks


def display_glb(source: bytes) -> tuple[bytes, dict]:
    doc, chunks = unpack_glb(source)
    assert doc["scenes"][doc.get("scene", 0)]["nodes"] == [0]
    root = doc["nodes"][0]
    assert root.get("name") == "world"
    assert not any(k in root for k in ("matrix", "rotation", "translation", "scale")), "Transform already applied"
    assert len(doc["meshes"]) == 1377, "Unexpected baseline; audit before upgrading"
    nodes = {node.get("name") for node in doc["nodes"]}
    for name in ["LAKE_00", "LAKE_04", "SHORE_00", "SHORE_04", "ROAD_000", "ROAD_001"]:
        assert name in nodes
    root["rotation"] = Y_UP
    doc.setdefault("asset", {}).setdefault("extras", {})["bnbu_scene_transform"] = {
        "source": "BNBU_v64_ACTIVE.glb",
        "source_coords": "X=easting,Y=northing,Z=unsurveyed relative height",
        "display_coords": "glTF Y-up; X=easting,Y=height,Z=negative northing",
        "operation": "root rotation -90 degrees about X; mesh data unchanged",
        "surveyed": False,
    }
    payload = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chunks[0] = (b"JSON", payload + b" " * ((-len(payload)) % 4))
    assembled = b"".join(struct.pack("<I4s", len(blob), typ) + blob for typ, blob in chunks)
    out = b"glTF" + struct.pack("<II", 2, 12 + len(assembled)) + assembled
    output_doc, output_chunks = unpack_glb(out)
    assert output_doc["nodes"][0]["rotation"] == Y_UP
    assert chunks[1:] == output_chunks[1:]  # Preserve exact raw mesh binary
    return out, {"nodes": len(output_doc["nodes"]), "meshes": len(output_doc["meshes"]),
                 "source_sha256": hashlib.sha256(source).hexdigest(),
                 "display_sha256": hashlib.sha256(out).hexdigest(),
                 "mesh_chunks_sha256": [hashlib.sha256(x).hexdigest() for _, x in chunks[1:]]}


def reconcile_geojson(data: bytes, glb: bytes) -> tuple[bytes, dict]:
    doc = json.loads(data)
    base, _ = unpack_glb(glb)
    names = {node.get("name") for node in base["nodes"]}
    assert len(doc["features"]) == 522
    corrected, legacy = [], []
    for f in doc["features"]:
        p = f.get("properties") or {}
        old = p.get("model_node")
        kind = p.get("feature_type")
        if kind in ("water_pbr_material", "shore_grade"):
            assert old and old not in names, (kind, old)
            prefix = "V53_WATER_" if kind == "water_pbr_material" else "V53_SHORE_BANK_"
            assert old.startswith(prefix), old
            i = old[len(prefix):len(prefix) + 2]
            assert i in {"00", "01", "02", "03", "04"}
            new = ("LAKE_" if kind == "water_pbr_material" else "SHORE_") + i
            assert new in names
            p["v65_unresolved_historical_node"] = old
            p["render_model_node"] = new
            p["render_alias_only"] = 1
            p["is_surveyed"] = 0
            corrected.append((old, new))
        elif old:
            if old in names:
                p["render_model_node"] = old
            else:
                p["render_model_node"] = None
                p["v65_resolution"] = "historical mesh alias; no active node"
                legacy.append(old)
    assert len(corrected) == 10
    assert len(legacy) == 102
    doc["v65_display_only_provenance"] = {
        "source_version": "v64", "changed_geometry": False, "glb_mesh_data_mutated": False,
        "gis_coordinates_mutated": False,
        "note": "Render aliases are references, not surveys; missing legacy stairs are not recreated",
    }
    out = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(json.loads(out)["features"]) == len(doc["features"])
    return out, {"render_alias_repairs": len(corrected), "unresolved_legacy_references": len(legacy),
                 "alias_map": dict(corrected), "gis_features": len(doc["features"]),
                 "source_sha256": hashlib.sha256(data).hexdigest(),
                 "reconciled_sha256": hashlib.sha256(out).hexdigest()}


def build(dest=OUT) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    glb_v64 = source_bytes("BNBU_v64_ACTIVE.glb")
    geo_v64 = source_bytes("BNBU_v64_ACTIVE.geojson")
    corrected_glb, glb_stats = display_glb(glb_v64)
    corrected_geo, geo_stats = reconcile_geojson(geo_v64, glb_v64)
    (dest / "BNBU_v65_DISPLAY_Y_UP.glb").write_bytes(corrected_glb)
    (dest / "BNBU_v65_RENDER_REFERENCES.geojson").write_bytes(corrected_geo)
    summary = {"version": "v65-display-correction", "geometry": "identical inherited v64 mesh bytes",
               "elevation": "relative, not DEM or surveyed", "root_rotation": Y_UP,
               "display": glb_stats, "gis": geo_stats,
               "not_added": ["CTV unverified structure", "unmeasured paths",
                             "inferred lake margins", "invented glass"]}
    (dest / "v65_integrity_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    summary = build(args.out)
    print(json.dumps({"version": summary["version"], "nodes": summary["display"]["nodes"],
                      "meshes": summary["display"]["meshes"],
                      "repaired_render_references": summary["gis"]["render_alias_repairs"],
                      "unresolved_legacy_references": summary["gis"]["unresolved_legacy_references"]}, indent=2))
