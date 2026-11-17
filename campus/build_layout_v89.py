"""Build BNBU v89 layout-corrected, Blender-compatible 3D campus master scene.

Reconciles building positions, orientations, multi-wing footprints, heights,
skybridges (V52_00..05), Phase II dormitories & courtyard links, Phase II LRC,
Circular Commons, Sports Park, Huitong Village context, campus roads/paths,
and water bodies against 2025-06-10 WorldView-2 0.5m orthophoto & OSM vectors.

Outputs clean Binary glTF 2.0 (.glb) with outward normals, PBR materials,
Y-up root transform (Blender Z-up compatible at campus origin), updated sharp
feature edges, architecture atlas, asset registry, GIS footprints, and before/after QA.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import shapely
import shapely.prepared
from pyproj import Transformer
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, mapping
from shapely.ops import transform, unary_union, nearest_points

HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE / "evidence").exists() else HERE.parent
DATA = ROOT / "generated"
EVIDENCE = ROOT / "evidence"
REGISTRY_DIR = ROOT / "registry"

PARENT_GLB = DATA / "BNBU_v71_CONNECTED_LAKEFRONT.glb"
GROUND_TRUTH = EVIDENCE / "bnbu_layout_ground_truth_v89.json"

OUT_GLB = DATA / "BNBU_v89_LAYOUT_CORRECTED.glb"
OUT_EDGES = DATA / "BNBU_v89_SHARP_FEATURE_EDGES_DISPLAY_ONLY.glb"
OUT_ATLAS = DATA / "BNBU_v89_ARCHITECTURE_COMPONENT_ATLAS.json"
OUT_GEOJSON = DATA / "BNBU_v89_RESOLVED_REFERENCES.geojson"
OUT_AUDIT = DATA / "BNBU_v89_LAYOUT_AUDIT_REPORT.json"
OUT_REG_JSON = REGISTRY_DIR / "BNBU_v89_BUILDING_ASSET_REGISTRY.json"
OUT_REG_CSV = REGISTRY_DIR / "BNBU_v89_BUILDING_ASSET_REGISTRY.csv"

OFFSET_X, OFFSET_Y = 758940.0, 2474080.0
Y_UP = [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]
TO_WGS = Transformer.from_crs("EPSG:32649", "EPSG:4326", always_xy=True).transform
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32649", always_xy=True).transform


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def unpack_glb(data: bytes) -> tuple[dict, bytes]:
    assert data[:4] == b"glTF" and struct.unpack_from("<II", data, 4) == (2, len(data))
    off = 12
    chunks = []
    while off < len(data):
        n, typ = struct.unpack_from("<I4s", data, off)
        off += 8
        chunks.append((typ, data[off : off + n]))
        off += n
    assert chunks[0][0] == b"JSON" and chunks[1][0] == b"BIN\0"
    doc = json.loads(chunks[0][1].decode("utf-8").rstrip(" \t\r\n\0"))
    return doc, chunks[1][1]


def pack_glb(doc: dict, binary: bytes) -> bytes:
    j = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    j += b" " * ((-len(j)) % 4)
    binary = bytes(binary) + b"\0" * ((-len(binary)) % 4)
    body = struct.pack("<I4s", len(j), b"JSON") + j + struct.pack("<I4s", len(binary), b"BIN\0") + binary
    return b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body


# ---------------------------------------------------------------------------
# Clean Triangulation & Extrusion Helpers (Shapely 2.2 CDT -> Split Normals)
# ---------------------------------------------------------------------------

def rings_to_polygon(ring_spec: dict) -> Polygon:
    holes = [h for h in ring_spec.get("holes", []) if len(h) >= 3]
    p = Polygon(ring_spec["outer"], holes)
    if not p.is_valid:
        p = p.buffer(0)
    return p


def triangulate_polygon_2d(poly: Polygon) -> list[np.ndarray]:
    """Return list of (3, 2) CCW triangles strictly inside `poly` (supports holes)."""
    if poly.is_empty or poly.area < 1e-4:
        return []
    polys = [poly] if poly.geom_type == "Polygon" else [g for g in poly.geoms if g.geom_type == "Polygon"]
    tris_2d = []
    for sub in polys:
        if sub.area < 1e-4:
            continue
        cdt = shapely.constrained_delaunay_triangles(sub)
        for g in cdt.geoms:
            if g.geom_type != "Polygon" or g.area < 1e-6:
                continue
            coords = np.asarray(g.exterior.coords[:3], dtype=np.float64)
            # Ensure CCW orientation in XY
            cross = (coords[1, 0] - coords[0, 0]) * (coords[2, 1] - coords[0, 1]) - (
                coords[2, 0] - coords[0, 0]
            ) * (coords[1, 1] - coords[0, 1])
            if cross < 0:
                coords = coords[[0, 2, 1]]
            tris_2d.append(coords)
    return tris_2d


def normalize_rows(v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(v, axis=-1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    return v / norms


def make_flat_mesh_arrays(tri_positions: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Given (N, 3, 3) triangles with CCW outward winding, return split POSITION, NORMAL, INDICES."""
    if len(tri_positions) == 0:
        return np.empty((0, 3), dtype="<f4"), np.empty((0, 3), dtype="<f4"), np.empty((0,), dtype="<u4")
    e1 = tri_positions[:, 1] - tri_positions[:, 0]
    e2 = tri_positions[:, 2] - tri_positions[:, 0]
    face_n = np.cross(e1, e2)
    areas = 0.5 * np.linalg.norm(face_n, axis=1)
    keep = areas > 1e-7
    tri_positions = tri_positions[keep]
    face_n = normalize_rows(face_n[keep])
    if len(tri_positions) == 0:
        return np.empty((0, 3), dtype="<f4"), np.empty((0, 3), dtype="<f4"), np.empty((0,), dtype="<u4")
    pos = tri_positions.reshape(-1, 3).astype("<f4")
    nrm = np.repeat(face_n[:, None, :], 3, axis=1).reshape(-1, 3).astype("<f4")
    idx = np.arange(len(pos), dtype="<u4")
    return pos, nrm, idx


def extrude_polygon_tris(poly: Polygon, z0: float, z1: float, cap_bottom: bool = True) -> np.ndarray:
    """Extrude arbitrary Shapely Polygon/MultiPolygon with holes to watertight CCW (N, 3, 3) tris."""
    if z1 <= z0 + 1e-4 or poly.is_empty:
        return np.empty((0, 3, 3), dtype=np.float64)
    polys = [poly] if poly.geom_type == "Polygon" else [g for g in poly.geoms if g.geom_type == "Polygon"]
    all_tris = []
    for sub in polys:
        if sub.area < 1e-4:
            continue
        # Ensure canonical orientation: exterior CCW, interiors CW
        sub_norm = shapely.orient_polygons(sub, exterior_cw=False)
        tris2d = triangulate_polygon_2d(sub_norm)
        for t in tris2d:
            # Top cap CCW (+Z normal)
            all_tris.append([[t[0, 0], t[0, 1], z1], [t[1, 0], t[1, 1], z1], [t[2, 0], t[2, 1], z1]])
            if cap_bottom:
                # Bottom cap CW in XY (-Z normal)
                all_tris.append([[t[0, 0], t[0, 1], z0], [t[2, 0], t[2, 1], z0], [t[1, 0], t[1, 1], z0]])
        # Side walls: exterior CCW means outward normal is to the right of p0->p1
        ring_list = [sub_norm.exterior] + list(sub_norm.interiors)
        for ring in ring_list:
            pts = np.asarray(ring.coords, dtype=np.float64)
            for k in range(len(pts) - 1):
                x0, y0 = pts[k]
                x1, y1 = pts[k + 1]
                if math.hypot(x1 - x0, y1 - y0) < 1e-5:
                    continue
                p0b = [x0, y0, z0]
                p1b = [x1, y1, z0]
                p1t = [x1, y1, z1]
                p0t = [x0, y0, z1]
                all_tris.append([p0b, p1b, p1t])
                all_tris.append([p0b, p1t, p0t])
    if not all_tris:
        return np.empty((0, 3, 3), dtype=np.float64)
    return np.asarray(all_tris, dtype=np.float64)


def cylinder_tris(cx: float, cy: float, radius: float, z0: float, z1: float, segs: int = 36) -> np.ndarray:
    angs = np.linspace(0, 2 * math.pi, segs + 1)
    ring = [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in angs]
    return extrude_polygon_tris(Polygon(ring), z0, z1)


def gable_prism_tris(poly: Polygon, z0: float, z1: float, ridge_h: float = 1.6) -> tuple[np.ndarray, np.ndarray]:
    """Return `(wall_tris, roof_tris)` with verified outward CCW normals for a gable/hipped house."""
    body = extrude_polygon_tris(poly, z0, z1)
    poly_ccw = shapely.orient_polygons(poly, exterior_cw=False)
    mrr = poly_ccw.minimum_rotated_rectangle
    coords = np.asarray(mrr.exterior.coords[:4], dtype=np.float64)
    e0 = coords[1] - coords[0]
    e1 = coords[2] - coords[1]
    if np.linalg.norm(e0) >= np.linalg.norm(e1):
        a = 0.5 * (coords[0] + coords[3])
        b = 0.5 * (coords[1] + coords[2])
    else:
        a = 0.5 * (coords[0] + coords[1])
        b = 0.5 * (coords[2] + coords[3])
    r0 = 0.82 * a + 0.18 * b
    r1 = 0.18 * a + 0.82 * b
    mid = 0.5 * (r0 + r1)
    pts = np.asarray(poly_ccw.exterior.coords[:-1], dtype=np.float64)
    roof_tris = []
    if len(pts) == 4:
        v_dir = r1 - r0
        v_dir /= max(np.linalg.norm(v_dir), 1e-9)
        proj = [float(np.dot(pt - mid, v_dir)) for pt in pts]
        neg = [i for i, pr in enumerate(proj) if pr < 0]
        pos = [i for i, pr in enumerate(proj) if pr >= 0]
        if len(neg) == 2 and len(pos) == 2:
            perp = np.array([-v_dir[1], v_dir[0]])
            neg_a = min(neg, key=lambda i: float(np.dot(pts[i] - mid, perp)))
            neg_b = max(neg, key=lambda i: float(np.dot(pts[i] - mid, perp)))
            pos_a = min(pos, key=lambda i: float(np.dot(pts[i] - mid, perp)))
            pos_b = max(pos, key=lambda i: float(np.dot(pts[i] - mid, perp)))
            rn = 0.5 * (pts[neg_a] + pts[neg_b])
            rp = 0.5 * (pts[pos_a] + pts[pos_b])
            rn3 = [rn[0], rn[1], z1 + ridge_h]
            rp3 = [rp[0], rp[1], z1 + ridge_h]
            p_na, p_pa = [pts[neg_a][0], pts[neg_a][1], z1], [pts[pos_a][0], pts[pos_a][1], z1]
            p_nb, p_pb = [pts[neg_b][0], pts[neg_b][1], z1], [pts[pos_b][0], pts[pos_b][1], z1]
            roof_tris.extend([
                [p_na, p_pa, rp3], [p_na, rp3, rn3],
                [p_pb, p_nb, rn3], [p_pb, rn3, rp3],
                [p_nb, p_na, rn3],
                [p_pa, p_pb, rp3],
            ])
    if not roof_tris:
        v = r1 - r0
        vv = float(np.dot(v, v))
        for k in range(len(pts)):
            p0 = pts[k]
            p1 = pts[(k + 1) % len(pts)]
            e_mid = 0.5 * (p0 + p1)
            t = float(np.clip(np.dot(e_mid - r0, v) / max(vv, 1e-9), 0.0, 1.0))
            apex_xy = r0 + t * v
            roof_tris.append([[p0[0], p0[1], z1], [p1[0], p1[1], z1], [apex_xy[0], apex_xy[1], z1 + ridge_h]])
    fixed = []
    for t in roof_tris:
        ta = np.asarray(t, dtype=np.float64)
        n = np.cross(ta[1] - ta[0], ta[2] - ta[0])
        if n[2] < 0:
            fixed.append([t[0], t[2], t[1]])
        else:
            fixed.append(t)
    # Add eave soffit cap facing down (-Z) only where roof sits on z1 (closed solid for Blender)
    soffit = extrude_polygon_tris(poly_ccw, z1 - 0.05, z1, cap_bottom=True)
    roof_all = np.vstack([soffit, np.asarray(fixed, dtype=np.float64)]) if len(soffit) else np.asarray(fixed, dtype=np.float64)
    return body, roof_all


def box_bar_tris(p0: np.ndarray, p1: np.ndarray, width: float, height: float) -> np.ndarray:
    """Create watertight outward-CCW rectangular beam connecting 3D points p0 and p1."""
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-5:
        return np.empty((0, 3, 3), dtype=np.float64)
    u = d / L
    ref = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
    s = np.cross(u, ref)
    s /= np.linalg.norm(s)
    t = np.cross(u, s)
    hw, hh = width * 0.5, height * 0.5
    c = [
        p0 - s * hw - t * hh,
        p0 + s * hw - t * hh,
        p0 + s * hw + t * hh,
        p0 - s * hw + t * hh,
        p1 - s * hw - t * hh,
        p1 + s * hw - t * hh,
        p1 + s * hw + t * hh,
        p1 - s * hw + t * hh,
    ]
    center = 0.5 * (p0 + p1)
    quads = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    tris = []
    for a, b, c_i, d_i in quads:
        for tri in ([c[a], c[b], c[c_i]], [c[a], c[c_i], c[d_i]]):
            ta = np.asarray(tri, dtype=np.float64)
            n = np.cross(ta[1] - ta[0], ta[2] - ta[0])
            out_dir = ta.mean(axis=0) - center
            tris.append(tri if np.dot(n, out_dir) >= 0 else [tri[0], tri[2], tri[1]])
    return np.asarray(tris, dtype=np.float64)


# ---------------------------------------------------------------------------
# Source GLB Triangle Reader & Normal Builder
# ---------------------------------------------------------------------------

def extract_source_tris(doc: dict, binary: bytes, node_name: str) -> np.ndarray:
    node = next((n for n in doc["nodes"] if n.get("name") == node_name and "mesh" in n), None)
    if node is None:
        return np.empty((0, 3, 3), dtype=np.float64)
    mesh = doc["meshes"][node["mesh"]]
    out = []
    for prim in mesh["primitives"]:
        acc_p = doc["accessors"][prim["attributes"]["POSITION"]]
        bv_p = doc["bufferViews"][acc_p["bufferView"]]
        off_p = bv_p.get("byteOffset", 0) + acc_p.get("byteOffset", 0)
        stride = bv_p.get("byteStride", 12)
        if stride == 12:
            v = np.frombuffer(binary, dtype="<f4", count=acc_p["count"] * 3, offset=off_p).reshape(-1, 3)
        else:
            v = np.array([struct.unpack_from("<fff", binary, off_p + stride * i) for i in range(acc_p["count"])])
        if "indices" in prim:
            acc_i = doc["accessors"][prim["indices"]]
            bv_i = doc["bufferViews"][acc_i["bufferView"]]
            off_i = bv_i.get("byteOffset", 0) + acc_i.get("byteOffset", 0)
            dt = {5123: "<u2", 5125: "<u4"}[acc_i["componentType"]]
            ind = np.frombuffer(binary, dtype=dt, count=acc_i["count"], offset=off_i).reshape(-1, 3)
            out.append(v[ind].astype(np.float64))
        else:
            out.append(v.reshape(-1, 3, 3).astype(np.float64))
    return np.vstack(out) if out else np.empty((0, 3, 3), dtype=np.float64)


def transform_tris_xy(tris: np.ndarray, origin_xy: tuple[float, float], deg: float, dx: float, dy: float) -> np.ndarray:
    if len(tris) == 0:
        return tris
    out = tris.copy()
    ox, oy = origin_xy
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    px = out[..., 0] - ox
    py = out[..., 1] - oy
    out[..., 0] = ox + px * c - py * s + dx
    out[..., 1] = oy + px * s + py * c + dy
    return out


# ---------------------------------------------------------------------------
# glTF 2.0 Scene Builder (Strict Blender-Compatible PBR + Normals)
# ---------------------------------------------------------------------------

class GLBBuilder:
    def __init__(self):
        self.materials = []
        self.mat_map = {}
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.nodes = [{"name": "world", "rotation": Y_UP, "children": []}]
        self.binary = bytearray()
        self.groups = {}

    def ensure_material(self, name: str, rgba: list[float], roughness: float = 0.78, metallic: float = 0.05,
                        double_sided: bool = True, alpha_mode: str = "OPAQUE") -> int:
        if name in self.mat_map:
            return self.mat_map[name]
        mat = {
            "name": name,
            "doubleSided": double_sided,
            "pbrMetallicRoughness": {
                "baseColorFactor": [round(float(x), 4) for x in rgba],
                "metallicFactor": round(float(metallic), 4),
                "roughnessFactor": round(float(roughness), 4),
            },
        }
        if alpha_mode == "BLEND":
            mat["alphaMode"] = "BLEND"
        idx = len(self.materials)
        self.materials.append(mat)
        self.mat_map[name] = idx
        return idx

    def ensure_group(self, layer_key: str, description: str) -> int:
        gname = "BNBU_GROUP_" + layer_key.upper()
        if gname in self.groups:
            return self.groups[gname]
        idx = len(self.nodes)
        self.nodes.append({
            "name": gname,
            "children": [],
            "extras": {
                "layer": layer_key,
                "evidence": description,
                "surveyed": False,
                "metric_birdstrike_eligible": False,
            },
        })
        self.nodes[0]["children"].append(idx)
        self.groups[gname] = idx
        return idx

    def add_mesh(self, node_name: str, layer_key: str, tris: np.ndarray, mat_name: str,
                 extras: dict | None = None, cap_bottom: bool = False) -> bool:
        pos, nrm, idx = make_flat_mesh_arrays(tris)
        if len(pos) == 0 or len(idx) == 0:
            return False
        # Pad binary buffer to 4-byte boundary before each view
        pos_bytes = pos.tobytes()
        nrm_bytes = nrm.tobytes()
        idx_bytes = idx.tobytes()

        off_pos = len(self.binary)
        self.binary.extend(pos_bytes)
        self.binary.extend(b"\0" * ((-len(self.binary)) % 4))

        off_nrm = len(self.binary)
        self.binary.extend(nrm_bytes)
        self.binary.extend(b"\0" * ((-len(self.binary)) % 4))

        off_idx = len(self.binary)
        self.binary.extend(idx_bytes)
        self.binary.extend(b"\0" * ((-len(self.binary)) % 4))

        bv_pos = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": off_pos, "byteLength": len(pos_bytes), "target": 34962})
        bv_nrm = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": off_nrm, "byteLength": len(nrm_bytes), "target": 34962})
        bv_idx = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": off_idx, "byteLength": len(idx_bytes), "target": 34963})

        acc_pos = len(self.accessors)
        self.accessors.append({
            "bufferView": bv_pos, "componentType": 5126, "count": int(len(pos)), "type": "VEC3",
            "min": [round(float(x), 6) for x in pos.min(axis=0)],
            "max": [round(float(x), 6) for x in pos.max(axis=0)],
        })
        acc_nrm = len(self.accessors)
        self.accessors.append({
            "bufferView": bv_nrm, "componentType": 5126, "count": int(len(nrm)), "type": "VEC3",
            "min": [round(float(x), 6) for x in nrm.min(axis=0)],
            "max": [round(float(x), 6) for x in nrm.max(axis=0)],
        })
        acc_idx = len(self.accessors)
        self.accessors.append({
            "bufferView": bv_idx, "componentType": 5125, "count": int(len(idx)), "type": "SCALAR",
            "min": [0], "max": [int(idx.max())],
        })

        mesh_extras = dict(extras or {})
        mesh_extras.setdefault("is_surveyed", False)
        mesh_extras.setdefault("bird_glass_denominator", False)
        mesh_idx = len(self.meshes)
        self.meshes.append({
            "name": node_name,
            "primitives": [{
                "attributes": {"POSITION": acc_pos, "NORMAL": acc_nrm},
                "indices": acc_idx,
                "material": self.mat_map[mat_name],
            }],
            "extras": mesh_extras,
        })
        node_idx = len(self.nodes)
        self.nodes.append({"name": node_name, "mesh": mesh_idx, "extras": mesh_extras})
        grp_idx = self.groups["BNBU_GROUP_" + layer_key.upper()]
        self.nodes[grp_idx]["children"].append(node_idx)
        return True

    def to_glb(self) -> bytes:
        doc = {
            "asset": {
                "version": "2.0",
                "generator": "BNBU v89 Layout-Corrected Campus Builder (Blender-Compatible)",
                "extras": {
                    "crs": "EPSG:32649",
                    "local_origin_utm49n": [OFFSET_X, OFFSET_Y],
                    "vertical_datum": "model_relative_z",
                    "reference_imagery": "ArcGIS WorldView-2 2025-06-10 (0.5m) + OSM 2026-11",
                    "surveyed": False,
                },
            },
            "scene": 0,
            "scenes": [{"name": "BNBU_Campus_v89", "nodes": [0]}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "bufferViews": self.buffer_views,
            "accessors": self.accessors,
            "buffers": [{"byteLength": len(self.binary)}],
        }
        return pack_glb(doc, bytes(self.binary))


# ---------------------------------------------------------------------------
# Architectural Builders
# ---------------------------------------------------------------------------

def init_palette(b: GLBBuilder):
    b.ensure_material("MAT_TERRAIN_HILLS", [0.41, 0.56, 0.37, 1.0], roughness=0.95, metallic=0.0)
    b.ensure_material("MAT_WATER_LAKE", [0.27, 0.48, 0.43, 1.0], roughness=0.22, metallic=0.05)
    b.ensure_material("MAT_SHORE_BANK", [0.75, 0.67, 0.50, 1.0], roughness=0.90, metallic=0.0)
    b.ensure_material("MAT_ROAD_ASPHALT", [0.27, 0.30, 0.33, 1.0], roughness=0.88, metallic=0.02)
    b.ensure_material("MAT_WALK_STONE", [0.76, 0.74, 0.69, 1.0], roughness=0.85, metallic=0.0)
    b.ensure_material("MAT_COURTYARD_GRASS", [0.42, 0.61, 0.36, 1.0], roughness=0.92, metallic=0.0)
    b.ensure_material("MAT_BOARDWALK_WOOD", [0.68, 0.49, 0.34, 1.0], roughness=0.78, metallic=0.02)
    b.ensure_material("MAT_BRIDGE_STEEL", [0.58, 0.62, 0.65, 1.0], roughness=0.50, metallic=0.35)
    b.ensure_material("MAT_SPORTS_TRACK", [0.66, 0.30, 0.25, 1.0], roughness=0.85, metallic=0.0)
    b.ensure_material("MAT_SPORTS_PITCH", [0.23, 0.48, 0.27, 1.0], roughness=0.90, metallic=0.0)
    b.ensure_material("MAT_SPORTS_TENNIS", [0.21, 0.43, 0.53, 1.0], roughness=0.82, metallic=0.0)
    b.ensure_material("MAT_SPORTS_BASKETBALL", [0.28, 0.49, 0.36, 1.0], roughness=0.82, metallic=0.0)

    # T Teaching Buildings
    b.ensure_material("MAT_T_WALL", [0.77, 0.67, 0.55, 1.0], roughness=0.82, metallic=0.02)
    b.ensure_material("MAT_T_STORYBAND", [0.90, 0.84, 0.75, 1.0], roughness=0.75, metallic=0.02)
    b.ensure_material("MAT_T_ROOF_DECK", [0.33, 0.37, 0.40, 1.0], roughness=0.86, metallic=0.05)
    b.ensure_material("MAT_T_PARAPET", [0.85, 0.80, 0.73, 1.0], roughness=0.78, metallic=0.02)
    b.ensure_material("MAT_T_PODIUM", [0.71, 0.68, 0.63, 1.0], roughness=0.85, metallic=0.02)

    # V Phase I Dormitories
    b.ensure_material("MAT_V_WALL", [0.74, 0.54, 0.42, 1.0], roughness=0.82, metallic=0.02)
    b.ensure_material("MAT_V_STORYBAND", [0.89, 0.82, 0.73, 1.0], roughness=0.76, metallic=0.02)
    b.ensure_material("MAT_V_ROOF_DECK", [0.32, 0.35, 0.36, 1.0], roughness=0.85, metallic=0.04)
    b.ensure_material("MAT_V_PARAPET", [0.86, 0.79, 0.71, 1.0], roughness=0.78, metallic=0.02)

    # D Phase II Dormitories
    b.ensure_material("MAT_D_WALL", [0.85, 0.86, 0.84, 1.0], roughness=0.78, metallic=0.02)
    b.ensure_material("MAT_D_STORYBAND", [0.75, 0.77, 0.76, 1.0], roughness=0.76, metallic=0.04)
    b.ensure_material("MAT_D_ROOF_PV", [0.23, 0.27, 0.30, 1.0], roughness=0.65, metallic=0.15)
    b.ensure_material("MAT_D_ROOF_GARDEN", [0.40, 0.56, 0.34, 1.0], roughness=0.92, metallic=0.0)
    b.ensure_material("MAT_D_PARAPET", [0.90, 0.90, 0.88, 1.0], roughness=0.74, metallic=0.02)
    b.ensure_material("MAT_D_GATEHOUSE", [0.78, 0.80, 0.79, 1.0], roughness=0.76, metallic=0.04)

    # LRC, P2 LRC & Public Facilities
    b.ensure_material("MAT_LRC_WHITE_FRAME", [0.94, 0.94, 0.90, 1.0], roughness=0.55, metallic=0.08)
    b.ensure_material("MAT_LRC_WALL", [0.83, 0.85, 0.84, 1.0], roughness=0.72, metallic=0.05)
    b.ensure_material("MAT_LRC_ROOF", [0.42, 0.47, 0.50, 1.0], roughness=0.80, metallic=0.08)
    b.ensure_material("MAT_GLASS_PROXY", [0.38, 0.60, 0.73, 0.55], roughness=0.18, metallic=0.10, alpha_mode="BLEND")
    b.ensure_material("MAT_FACILITY_WALL", [0.78, 0.79, 0.80, 1.0], roughness=0.74, metallic=0.05)
    b.ensure_material("MAT_FACILITY_ACCENT", [0.64, 0.68, 0.72, 1.0], roughness=0.65, metallic=0.12)
    b.ensure_material("MAT_CANOPY_ROOF", [0.89, 0.91, 0.91, 1.0], roughness=0.55, metallic=0.15)
    b.ensure_material("MAT_VILLAGE_WALL", [0.80, 0.77, 0.71, 1.0], roughness=0.85, metallic=0.0)
    b.ensure_material("MAT_VILLAGE_ROOF", [0.42, 0.37, 0.34, 1.0], roughness=0.85, metallic=0.02)


def add_building_mass(b: GLBBuilder, prefix: str, parts: list[dict], palette: dict,
                      story_h: float, meta_extra: dict, exclude_bridge_links: bool = True) -> list[str]:
    """Extrude realistic architectural parts (walls + story reveal bands + parapet + roof deck)."""
    created = []
    roof_polys = []
    all_parts_tris = []

    for i, pt in enumerate(parts):
        if exclude_bridge_links and pt.get("role") == "bridge_link":
            continue
        z0, z1 = float(pt["z_min"]), float(pt["z_max"])
        poly = unary_union([rings_to_polygon(r) for r in pt["rings"]])
        if poly.is_empty or poly.area < 0.5:
            continue

        # Main structural shell
        wall_tris = extrude_polygon_tris(poly, z0, z1)
        node_name = f"MAIN_{prefix}" if i == 0 and f"MAIN_{prefix}" not in created else f"{prefix}_PART_{i:02d}"
        if prefix.startswith("D") and i == 0:
            node_name = f"PHASEII_DORM_{prefix}"
        mat_wall = palette["gatehouse"] if pt.get("role") == "dorm_gatehouse_bridge" else (
            palette["podium"] if pt.get("levels", 3) <= 2 and prefix not in ("THEATRE", "P2_CIRCULAR_COMMONS") else palette["wall"]
        )
        ex = {**meta_extra, "part_role": pt.get("role", "wing"), "osm_id": pt.get("osm_id"), "levels": pt.get("levels")}
        if b.add_mesh(node_name, "architecture_opaque", wall_tris, mat_wall, ex):
            created.append(node_name)

        # Story reveal bands (purely architectural slab-edge lines, NOT glazing)
        band_tris = []
        lvl_start = max(1, int(round(z0 / max(story_h, 2.0))) + 1)
        lvl_end = int(round(z1 / max(story_h, 2.0)))
        outer_band = poly.buffer(0.10, join_style=2)
        inner_cut = poly.buffer(-0.08, join_style=2)
        if not outer_band.is_empty and not inner_cut.is_empty:
            band_ring = outer_band.difference(inner_cut)
            for k in range(lvl_start, lvl_end):
                zk = z0 + (k - lvl_start + 1) * ((z1 - z0) / max(lvl_end - lvl_start + 1, 1))
                if z0 + 0.6 < zk < z1 - 0.6:
                    bt = extrude_polygon_tris(band_ring, zk - 0.08, zk + 0.08)
                    if len(bt):
                        band_tris.append(bt)
        if band_tris:
            bname = f"V89_STORYBAND_{prefix}_{i:02d}"
            if b.add_mesh(bname, "architecture_opaque", np.vstack(band_tris), palette["band"],
                          {**meta_extra, "role": "story_slab_trim_not_glass"}):
                created.append(bname)

        # Raised parapet + roof deck on flat-roofed parts (>= 2F)
        if z1 >= 5.0 and pt.get("role") != "lrc_lakeside_canopy":
            inner_roof = poly.buffer(-0.45, join_style=2)
            if not inner_roof.is_empty and inner_roof.area > 4.0:
                parapet_ring = poly.difference(inner_roof)
                pt_tris = extrude_polygon_tris(parapet_ring, z1, z1 + 0.55)
                pname = f"ROOF_PARAPET_{prefix}" if f"ROOF_PARAPET_{prefix}" not in created else f"ROOF_PARAPET_{prefix}_{i:02d}"
                if b.add_mesh(pname, "architecture_opaque", pt_tris, palette["parapet"], ex):
                    created.append(pname)

                # Terrace green roof on 7F Phase II wings & 2F LRC terrace wings
                is_garden_roof = (
                    (prefix.startswith("D") and pt.get("role") == "dorm_terrace_wing")
                    or pt.get("role") == "lrc_terrace_wing"
                )
                rmat = palette.get("roof_garden", palette["roof"]) if is_garden_roof else palette["roof"]
                r_tris = extrude_polygon_tris(inner_roof, z1, z1 + 0.12)
                rname = f"ROOF_DECK_{prefix}" if f"ROOF_DECK_{prefix}" not in created else f"ROOF_DECK_{prefix}_{i:02d}"
                if b.add_mesh(rname, "architecture_opaque", r_tris, rmat, ex):
                    created.append(rname)
            else:
                r_tris = extrude_polygon_tris(poly, z1, z1 + 0.15)
                rname = f"ROOF_DECK_{prefix}" if f"ROOF_DECK_{prefix}" not in created else f"ROOF_DECK_{prefix}_{i:02d}"
                if b.add_mesh(rname, "architecture_opaque", r_tris, palette["roof"], ex):
                    created.append(rname)

    return created


def build_lrc_phase1(b: GLBBuilder, src_doc: dict, src_bin: bytes, bldg: dict, meta_extra: dict) -> list[str]:
    """Reconstruct accurate LRC: aligned 4F diagrid cube + stilts + skylight + 2F green wings + steps."""
    created = []
    # Main 4F cube (`664082914`) centered ~ (166.5, -62.5) local UTM -> rotated -21.34 deg
    # Wait: visually verified on WV02 `inspect_lrc_p2lrc_grids.png`: full 4F white parapet square extends
    # ~49.5m x 49.5m centered at local (166.5, -62.5) [UTM 759106.5, 2474017.5], rotated -21.34 deg.
    cx, cy = 166.5, -62.5
    ang_deg = -21.34
    th = math.radians(ang_deg)
    u = np.array([math.cos(th), math.sin(th)])
    v = np.array([-math.sin(th), math.cos(th)])
    hw, hh = 24.5, 24.0  # 49m x 48m matching white parapet outer rim in WV02

    corners = [
        (cx - hw * u[0] - hh * v[0], cy - hw * u[1] - hh * v[1]),
        (cx + hw * u[0] - hh * v[0], cy + hw * u[1] - hh * v[1]),
        (cx + hw * u[0] + hh * v[0], cy + hw * u[1] + hh * v[1]),
        (cx - hw * u[0] + hh * v[0], cy - hw * u[1] + hh * v[1]),
    ]
    cube_poly = Polygon(corners)

    # Central circular skylight hole (r=10.7m matching LRC_SKYLIGHT_RIM span 21.4m!)
    sky_cx, sky_cy = cx - 3.0 * u[0] + 1.5 * v[0], cy - 3.0 * u[1] + 1.5 * v[1]  # matches dark skylight circle in WV02
    hole_ring = [(sky_cx + 10.6 * math.cos(2 * math.pi * k / 36), sky_cy + 10.6 * math.sin(2 * math.pi * k / 36)) for k in range(36)]
    atrium_wall_poly = cube_poly.difference(Polygon(hole_ring))

    # 1. Raised 4F cube glazing proxy core (z=3.1 to 17.0, inset 0.45m)
    glass_core = cube_poly.buffer(-0.45).difference(Polygon(hole_ring).buffer(0.8))
    if b.add_mesh("V34_MODULE_V32_LRC_GLASS_FACADE_PROXY", "glass_proxies_unregistered",
                  extrude_polygon_tris(glass_core, 3.3, 16.9), "MAT_GLASS_PROXY",
                  {**meta_extra, "role": "visual_curtainwall_proxy_not_exposure_area"}):
        created.append("V34_MODULE_V32_LRC_GLASS_FACADE_PROXY")

    # 2. Raised floor soffit slab (z=3.0..3.4) & Roof slab with central skylight opening (z=16.9..17.3)
    if b.add_mesh("V40_MAIN_LRC_FACADE_AND_SIDEWALLS", "architecture_opaque",
                  extrude_polygon_tris(cube_poly, 3.0, 3.45), "MAT_LRC_WHITE_FRAME", meta_extra):
        created.append("V40_MAIN_LRC_FACADE_AND_SIDEWALLS")
    if b.add_mesh("ROOF_DECK_LRC", "architecture_opaque",
                  extrude_polygon_tris(atrium_wall_poly, 16.9, 17.35), "MAT_LRC_ROOF", meta_extra):
        created.append("ROOF_DECK_LRC")
    parapet_ring = cube_poly.difference(cube_poly.buffer(-0.65))
    if b.add_mesh("ROOF_PARAPET_LRC", "architecture_opaque",
                  extrude_polygon_tris(parapet_ring, 17.35, 17.95), "MAT_LRC_WHITE_FRAME", meta_extra):
        created.append("ROOF_PARAPET_LRC")

    # 3. Skylight rim & translucent dome glazing
    sky_outer = Polygon([(sky_cx + 11.2 * math.cos(2 * math.pi * k / 36), sky_cy + 11.2 * math.sin(2 * math.pi * k / 36)) for k in range(36)])
    sky_inner = Polygon(hole_ring)
    if b.add_mesh("LRC_SKYLIGHT_RIM", "architecture_opaque",
                  extrude_polygon_tris(sky_outer.difference(sky_inner), 17.25, 17.95), "MAT_LRC_WHITE_FRAME", meta_extra):
        created.append("LRC_SKYLIGHT_RIM")
    if b.add_mesh("LRC_DOME_GLAZING_APPROX", "glass_proxies_unregistered",
                  extrude_polygon_tris(sky_inner, 17.35, 17.65), "MAT_GLASS_PROXY", meta_extra):
        created.append("LRC_DOME_GLAZING_APPROX")

    # 4. Perimeter colonnade stilts (z=0..3.1m) + iconic white facade diagonal braces!
    stilt_tris = []
    brace_tris = []
    edges = [(corners[k], corners[(k + 1) % 4]) for k in range(4)]
    for ea, eb in edges:
        pa, pb = np.array(ea), np.array(eb)
        n_bays = 6
        for j in range(n_bays + 1):
            t0 = j / n_bays
            pt = pa * (1 - t0) + pb * t0
            stilt_tris.append(box_bar_tris(np.array([pt[0], pt[1], 0.0]), np.array([pt[0], pt[1], 3.1]), 0.55, 0.55))
            if j < n_bays:
                t1 = (j + 1) / n_bays
                q0 = pa * (1 - t0) + pb * t0
                q1 = pa * (1 - t1) + pb * t1
                brace_tris.append(box_bar_tris(np.array([q0[0], q0[1], 3.3]), np.array([q1[0], q1[1], 17.0]), 0.42, 0.42))
                brace_tris.append(box_bar_tris(np.array([q1[0], q1[1], 3.3]), np.array([q0[0], q0[1], 17.0]), 0.42, 0.42))
    if b.add_mesh("LRC_STILT_COLONNADE", "architecture_opaque", np.vstack(stilt_tris), "MAT_LRC_WHITE_FRAME", meta_extra):
        created.append("LRC_STILT_COLONNADE")
    if b.add_mesh("LRC_DIAGONAL_BRACE_SYSTEM", "architecture_opaque", np.vstack(brace_tris), "MAT_LRC_WHITE_FRAME", meta_extra):
        created.append("LRC_DIAGONAL_BRACE_SYSTEM")

    # 5. 2F green-roof terrace wings, cantilevered lakeside canopy & SW steps from OSM REL 20188781
    lrc_pal = {
        "wall": "MAT_LRC_WALL", "band": "MAT_LRC_WHITE_FRAME",
        "roof": "MAT_LRC_ROOF", "roof_garden": "MAT_COURTYARD_GRASS",
        "parapet": "MAT_LRC_WHITE_FRAME", "podium": "MAT_LRC_WALL", "gatehouse": "MAT_LRC_WALL",
    }
    lower_parts = [pt for pt in bldg["parts"] if pt["role"] != "lrc_main_cube"]
    created.extend(add_building_mass(b, "LRC_TERRACE", lower_parts, lrc_pal, 3.5, meta_extra))

    # Align source V48 exterior stair onto LRC SW terrace approach (facing quad)
    src_stair = extract_source_tris(src_doc, src_bin, "V48_LRC_EXISTING_18_TREAD_EXTERIOR_STAIR_CONNECTED_NOT_SURVEYED")
    if len(src_stair):
        sc = src_stair.reshape(-1, 3).mean(axis=0)
        # Move near LRC SW stepped plaza (1475182843 ctr ~ (152.6, -84.9) local) and align -21.34 deg
        aligned_stair = transform_tris_xy(src_stair, (sc[0], sc[1]), -21.34, 152.6 - sc[0], -84.9 - sc[1])
        if b.add_mesh("V48_LRC_EXISTING_18_TREAD_EXTERIOR_STAIR_CONNECTED_NOT_SURVEYED", "stairs_unsurveyed",
                      aligned_stair, "MAT_WALK_STONE", {**meta_extra, "role": "aligned_source_stair"}):
            created.append("V48_LRC_EXISTING_18_TREAD_EXTERIOR_STAIR_CONNECTED_NOT_SURVEYED")
    return created


# ---------------------------------------------------------------------------
# Main Build Routine
# ---------------------------------------------------------------------------

def build() -> dict:
    gt = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    src_doc, src_bin = unpack_glb(PARENT_GLB.read_bytes())

    builder = GLBBuilder()
    init_palette(builder)

    layers_desc = {
        "terrain_unsurveyed": "Hillside relief backdrop; vertices clamped beneath campus building/sports pads",
        "water_unsurveyed": "Verified WV02/OSM campus lake and ponds (false road lakes removed)",
        "shore_unsurveyed": "Retained shore relief aligned to campus waterfront",
        "vehicle_roads_unsurveyed": "WV02/OSM verified campus carriageways and perimeter ring roads",
        "pedestrian_paving_unsurveyed": "Campus pedestrian spine, Phase II ring & radials, sports courts",
        "ground_connectors_unsurveyed": "Retained lakeside east crossing ramp and V71 promenade joins",
        "elevated_boardwalk_unsurveyed": "Retained V60 lakeside timber boardwalk and pier supports",
        "stairs_unsurveyed": "Aligned exterior campus staircases",
        "glass_proxies_unregistered": "Translucent architectural facade zones (visual proxy only, NOT collision denominator)",
        "architecture_opaque": "Layout-corrected 41 campus buildings, multi-wing masses, skybridges, canopies & village context",
    }
    for lk, ldesc in layers_desc.items():
        builder.ensure_group(lk, ldesc)

    meta_base = {
        "evidence_source": "WV02_2025-06-10 + OSM_2026-11",
        "footprint_verified": True,
        "is_surveyed": False,
        "bird_glass_denominator": False,
    }

    # Precompute built exclusion zones (buildings + sports park + verified lakes) to clamp terrain relief
    built_pads = []
    for bldg in gt["buildings"]:
        for r in bldg["footprint_rings"]:
            built_pads.append(rings_to_polygon(r).buffer(3.0))
    for sp in gt["sports_park"]:
        for r in sp["rings"]:
            built_pads.append(rings_to_polygon(r).buffer(4.0))
    for wt in gt["waters"]:
        for r in wt["rings"]:
            built_pads.append(rings_to_polygon(r).buffer(2.0))
    built_union = unary_union(built_pads)
    prep_built = shapely.prepared.prep(built_union)

    # 1. Retained V53 Hillside Terrain Relief (with points inside built pads clamped safely below grade)
    for tname in sorted(n.get("name") for n in src_doc["nodes"] if "TERRAIN_RELIEF" in n.get("name", "")):
        tris = extract_source_tris(src_doc, src_bin, tname)
        if len(tris):
            flat = tris.reshape(-1, 3)
            for k in range(len(flat)):
                if flat[k, 2] > -0.15 and prep_built.contains(shapely.Point(flat[k, 0], flat[k, 1])):
                    flat[k, 2] = -0.22
            builder.add_mesh(tname, "terrain_unsurveyed", tris, "MAT_TERRAIN_HILLS",
                             {"role": "terrain_relief_clamped_outside_buildings", "is_surveyed": False})

    # 2. Retained Lakefront Waterfront Context (V60 boardwalk, piers, crossbeams, V61 slabs, V54 east ramp, V71 seams, SHORE_00/02)
    retained_nodes = [
        ("V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE", "elevated_boardwalk_unsurveyed", "MAT_BOARDWALK_WOOD"),
        ("V54_LAKE00_EAST_WATER_CROSSING_SHORE_RAMP_INFERRED_ENDPOINT_MATCH", "ground_connectors_unsurveyed", "MAT_BOARDWALK_WOOD"),
        ("V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_01_NOT_SURVEYED", "ground_connectors_unsurveyed", "MAT_WALK_STONE"),
        ("V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_02_NOT_SURVEYED", "ground_connectors_unsurveyed", "MAT_WALK_STONE"),
        ("V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_01_UNSURVEYED", "architecture_opaque", "MAT_WALK_STONE"),
        ("V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_02_UNSURVEYED", "architecture_opaque", "MAT_WALK_STONE"),
        ("V61_P1_LRC_SHORE_PROMENADE_RETOPOLOGIZED_OPAQUE_SLAB_03_UNSURVEYED", "architecture_opaque", "MAT_WALK_STONE"),
        ("SHORE_00", "shore_unsurveyed", "MAT_SHORE_BANK"),
        ("SHORE_02", "shore_unsurveyed", "MAT_SHORE_BANK"),
    ]
    for nm in sorted(n.get("name") for n in src_doc["nodes"] if "V60_P1_EASTLAKE_BOARDWALK_" in n.get("name", "")):
        if nm != retained_nodes[0][0]:
            retained_nodes.append((nm, "elevated_boardwalk_unsurveyed", "MAT_BOARDWALK_WOOD"))
    for nm, lk, mat in retained_nodes:
        tris = extract_source_tris(src_doc, src_bin, nm)
        if len(tris):
            builder.add_mesh(nm, lk, tris, mat, {"role": "retained_lakefront_source", "is_surveyed": False})

    # 3. Verified Campus Water Bodies (LAKE_00 with island, LAKE_02, plus verified real ponds)
    for wt in gt["waters"]:
        poly = unary_union([rings_to_polygon(r) for r in wt["rings"]])
        tris = extrude_polygon_tris(poly, wt["z_min"], wt["z_max"])
        builder.add_mesh(wt["name"], "water_unsurveyed", tris, "MAT_WATER_LAKE",
                         {**meta_base, "osm_id": wt["osm_id"], "role": "verified_water_body"})

    # 4. Verified Campus Roads, Walkways, Plazas & Grass Lawns
    road_poly = unary_union([rings_to_polygon(r) for r in gt["campus_roads_rings"]])
    builder.add_mesh("V89_CAMPUS_VEHICLE_ROADS_NETWORK", "vehicle_roads_unsurveyed",
                     extrude_polygon_tris(road_poly, -0.08, 0.01), "MAT_ROAD_ASPHALT",
                     {**meta_base, "role": "verified_osm_wv02_carriageways"})

    walk_poly = unary_union([rings_to_polygon(r) for r in gt["campus_walkways_rings"]])
    builder.add_mesh("V89_CAMPUS_PEDESTRIAN_WALKWAYS", "pedestrian_paving_unsurveyed",
                     extrude_polygon_tris(walk_poly, -0.06, 0.03), "MAT_WALK_STONE",
                     {**meta_base, "role": "verified_osm_wv02_walkways"})

    # Retain Phase II inner circular ring paving & radial D1-D6 paving cleanly (extending radials into dorm courtyards)
    for nm in sorted(n.get("name") for n in src_doc["nodes"]
                     if n.get("name", "").startswith("PHASEII_V12_PAVING_phaseII_inner_college_ring")):
        tris = extract_source_tris(src_doc, src_bin, nm)
        if len(tris):
            builder.add_mesh(nm, "pedestrian_paving_unsurveyed", tris, "MAT_WALK_STONE",
                             {**meta_base, "role": "phaseii_inner_ring_paving"})

    grass_poly = unary_union([rings_to_polygon(r) for r in gt["campus_grass_rings"]])
    builder.add_mesh("V89_CAMPUS_LAWN_AND_COURTYARD_GREENS", "pedestrian_paving_unsurveyed",
                     extrude_polygon_tris(grass_poly, -0.05, 0.045), "MAT_COURTYARD_GRASS",
                     {**meta_base, "role": "verified_campus_lawns"})

    # 5. Sports Park (Track, Pitch, 6 Tennis Courts, 4 Basketball Courts at real coordinates!)
    role_mat = {"track": "MAT_SPORTS_TRACK", "pitch": "MAT_SPORTS_PITCH", "tennis": "MAT_SPORTS_TENNIS", "basketball": "MAT_SPORTS_BASKETBALL"}
    for sp in gt["sports_park"]:
        poly = unary_union([rings_to_polygon(r) for r in sp["rings"]])
        tris = extrude_polygon_tris(poly, sp["z_min"], sp["z_max"])
        builder.add_mesh(sp["name"], "pedestrian_paving_unsurveyed", tris, role_mat[sp["role"]],
                         {**meta_base, "role": f"sports_{sp['role']}"})

    # 6. Covered Walkways & Canopies + Support Columns
    for can in gt["canopies"]:
        poly = unary_union([rings_to_polygon(r) for r in can["rings"]])
        tris = extrude_polygon_tris(poly, can["z_min"], can["z_max"])
        builder.add_mesh(can["name"], "architecture_opaque", tris, "MAT_CANOPY_ROOF",
                         {**meta_base, "osm_id": can["osm_id"], "role": "covered_walkway_canopy"})
        # Add clean cylindrical support posts sampled every ~10m along canopy centerline/perimeter
        cols = []
        pts = list(poly.exterior.coords)
        step = max(1, len(pts) // 8)
        for pt in pts[::step]:
            # inset slightly toward centroid
            c = poly.centroid
            px, py = 0.85 * pt[0] + 0.15 * c.x, 0.85 * pt[1] + 0.15 * c.y
            cols.append(cylinder_tris(px, py, 0.14, 0.0, can["z_min"], segs=8))
        if cols:
            builder.add_mesh(can["name"] + "_COLUMNS", "architecture_opaque", np.vstack(cols), "MAT_BRIDGE_STEEL",
                             {**meta_base, "role": "canopy_support_columns_illustrative"})

    # 7. Huitong Living Village Context (`V14_LIVING_VILLAGE`, accurately positioned on real Huitong villas!)
    v_walls, v_roofs = [], []
    for vh in gt["village_villas"]:
        p = rings_to_polygon(vh["rings"][0])
        w_t, r_t = gable_prism_tris(p, vh["z_min"], max(vh["z_min"] + 1.5, vh["z_max"] - 1.5), ridge_h=1.6)
        if len(w_t):
            v_walls.append(w_t)
        if len(r_t):
            v_roofs.append(r_t)
    if v_walls:
        builder.add_mesh("V14_LIVING_VILLAGE_HUITONG_VILLAS_VERIFIED", "architecture_opaque",
                         np.vstack(v_walls), "MAT_VILLAGE_WALL",
                         {**meta_base, "role": "huitong_village_context_31_villas"})
    if v_roofs:
        builder.add_mesh("V14_LIVING_VILLAGE_HUITONG_ROOFS_VERIFIED", "architecture_opaque",
                         np.vstack(v_roofs), "MAT_VILLAGE_ROOF",
                         {**meta_base, "role": "huitong_village_gable_roofs"})

    # 8. Build ALL 41 Campus Buildings + V52 Bridges!
    palettes = {
        "T": {"wall": "MAT_T_WALL", "band": "MAT_T_STORYBAND", "roof": "MAT_T_ROOF_DECK", "parapet": "MAT_T_PARAPET", "podium": "MAT_T_PODIUM", "gatehouse": "MAT_T_PODIUM"},
        "V": {"wall": "MAT_V_WALL", "band": "MAT_V_STORYBAND", "roof": "MAT_V_ROOF_DECK", "parapet": "MAT_V_PARAPET", "podium": "MAT_V_WALL", "gatehouse": "MAT_V_WALL"},
        "D": {"wall": "MAT_D_WALL", "band": "MAT_D_STORYBAND", "roof": "MAT_D_ROOF_PV", "roof_garden": "MAT_D_ROOF_GARDEN", "parapet": "MAT_D_PARAPET", "podium": "MAT_D_WALL", "gatehouse": "MAT_D_GATEHOUSE"},
        "LRC": {"wall": "MAT_LRC_WALL", "band": "MAT_LRC_WHITE_FRAME", "roof": "MAT_LRC_ROOF", "roof_garden": "MAT_COURTYARD_GRASS", "parapet": "MAT_LRC_WHITE_FRAME", "podium": "MAT_LRC_WALL", "gatehouse": "MAT_LRC_WALL"},
        "OTHER": {"wall": "MAT_FACILITY_WALL", "band": "MAT_T_STORYBAND", "roof": "MAT_T_ROOF_DECK", "parapet": "MAT_T_PARAPET", "podium": "MAT_T_PODIUM", "gatehouse": "MAT_FACILITY_ACCENT"},
    }

    building_components_map = {}
    v52_bridge_map = {}  # id -> bridge poly/height from T4-T7 + T1-T2 links

    for bldg in gt["buildings"]:
        aid = bldg["id"]
        fam = bldg["family"]
        b_meta = {**meta_base, "building_id": aid, "family": fam}

        if aid == "LRC":
            comps = build_lrc_phase1(builder, src_doc, src_bin, bldg, b_meta)
        elif aid == "P2_CIRCULAR_COMMONS":
            # Shift all 11 exact detailed components by verified (+18.96, -13.93) onto OSM 1191618603!
            comps = []
            fp = unary_union([rings_to_polygon(r) for r in bldg["footprint_rings"]])
            base_tris = extract_source_tris(src_doc, src_bin, "V24_P2_CIRCULAR_COMMONS_01_BASE_PLINTH")
            cur_cx = float((base_tris[..., 0].min() + base_tris[..., 0].max()) * 0.5)
            cur_cy = float((base_tris[..., 1].min() + base_tris[..., 1].max()) * 0.5)
            dx, dy = fp.centroid.x - cur_cx, fp.centroid.y - cur_cy
            for nd in src_doc["nodes"]:
                nm = nd.get("name", "")
                if nm.startswith("V24_P2_CIRCULAR_COMMONS_"):
                    tris = extract_source_tris(src_doc, src_bin, nm)
                    shifted = transform_tris_xy(tris, (cur_cx, cur_cy), 0.0, dx, dy)
                    lk = "glass_proxies_unregistered" if "GLASS" in nm else "architecture_opaque"
                    mat = "MAT_GLASS_PROXY" if "GLASS" in nm else ("MAT_D_PARAPET" if "ROOF" in nm or "EAVE" in nm else "MAT_FACILITY_WALL")
                    if builder.add_mesh(nm, lk, shifted, mat, {**b_meta, "aligned_delta_xy": [round(dx, 3), round(dy, 3)]}):
                        comps.append(nm)
        else:
            pal = palettes[fam]
            comps = add_building_mass(builder, aid, bldg["parts"], pal, bldg["story_height_m"], b_meta)

            # Special recognizable roof domes/vaults matching WV02 imagery
            if aid == "HALL":
                # Circular auditorium rotunda at NE corner of HALL (`OSM 664082913` ~ local (165.0, -217.5))
                dome = cylinder_tris(165.0, -217.5, 12.2, 15.0, 18.6, segs=36)
                dome_cap = cylinder_tris(165.0, -217.5, 10.6, 18.6, 19.3, segs=36)
                if builder.add_mesh("HALL_AUDITORIUM_ROTUNDA_DRUM", "architecture_opaque", np.vstack([dome, dome_cap]), "MAT_LRC_WHITE_FRAME", b_meta):
                    comps.append("HALL_AUDITORIUM_ROTUNDA_DRUM")
            elif aid == "SPORT":
                # Arena upper roof crown (`90 x 51m` rotated ~138.8 deg -> inset 7m)
                fp = unary_union([rings_to_polygon(r) for r in bldg["footprint_rings"]]).buffer(-7.0, join_style=2)
                if not fp.is_empty:
                    crown = extrude_polygon_tris(fp, 18.0, 19.6)
                    if builder.add_mesh("SPORT_ARENA_UPPER_CROWN", "architecture_opaque", crown, "MAT_FACILITY_ACCENT", b_meta):
                        comps.append("SPORT_ARENA_UPPER_CROWN")
            elif aid == "P2_LRC_LAB_COMPLEX":
                # Add central sunken green courtyard lawn inside the actual atrium void!
                fp_lrc = unary_union([rings_to_polygon(r) for r in bldg["footprint_rings"]])
                if fp_lrc.geom_type == "Polygon" and fp_lrc.interiors:
                    court = Polygon(fp_lrc.interiors[0]).buffer(-0.6)
                    if not court.is_empty and court.area > 1.0:
                        builder.add_mesh("P2_LRC_ATRIUM_GARDEN_FLOOR", "pedestrian_paving_unsurveyed",
                                         extrude_polygon_tris(court, 0.0, 0.06), "MAT_COURTYARD_GRASS", b_meta)

        # Collect V52 elevated skybridges from T4..T7 parts + T1/T2 3F link bays
        for pt in bldg["parts"]:
            if pt.get("role") == "bridge_link":
                v52_bridge_map.setdefault(aid, []).append(pt)

        building_components_map[aid] = comps

    # 9. Build all 6 V52 Academic Bridges connecting T1-T2, T2-T3, T4-T5, T5-T6, T6-T7, T7-T8!
    bridge_defs = [
        ("V52_LEVEL2_PEDESTRIAN_CONNECTION_00_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "T4", ["T4", "T5"]),
        ("V52_LEVEL2_PEDESTRIAN_CONNECTION_01_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "T5", ["T5", "T6"]),
        ("V52_LEVEL2_PEDESTRIAN_CONNECTION_02_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "T6", ["T6", "T7"]),
        ("V52_LEVEL2_PEDESTRIAN_CONNECTION_03_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "T7", ["T7", "T8"]),
    ]
    for bnode, src_b, pair in bridge_defs:
        pt = v52_bridge_map[src_b][0]
        poly = unary_union([rings_to_polygon(r) for r in pt["rings"]])
        z0, z1 = float(pt["z_min"]), max(float(pt["z_min"]) + 3.2, float(pt["z_max"]))
        deck_t = extrude_polygon_tris(poly, z0, z0 + 0.45)
        roof_t = extrude_polygon_tris(poly, z1 - 0.35, z1)
        # Side enclosure proxy (curtain wall strip + steel framing)
        ring_p = poly.difference(poly.buffer(-0.25))
        side_t = extrude_polygon_tris(ring_p, z0 + 0.45, z1 - 0.35) if not ring_p.is_empty else np.empty((0, 3, 3))
        if builder.add_mesh(bnode, "architecture_opaque", np.vstack([deck_t, roof_t]), "MAT_T_PARAPET",
                            {**meta_base, "adjacent_blocks": pair, "role": "level2_skybridge_structure"}):
            building_components_map[src_b].append(bnode)
        if len(side_t):
            builder.add_mesh(bnode.replace("_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "_ENCLOSURE_PROXY"),
                             "glass_proxies_unregistered", side_t, "MAT_GLASS_PROXY",
                             {**meta_base, "adjacent_blocks": pair, "role": "bridge_visual_enclosure_not_surveyed_glass"})

    # V52_04 (T1<->T2) and V52_05 (T2<->T3): real 3F link bays (`1215776052` in T1, `1215776049` in T2)
    for bnode, src_aid, osm_part_id, pair in [
        ("V52_LEVEL2_PEDESTRIAN_CONNECTION_04_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "T1", 1215776052, ["T1", "T2"]),
        ("V52_LEVEL2_PEDESTRIAN_CONNECTION_05_CLOSED_SLAB_EXISTING_TOPOGRAPHY", "T2", 1215776049, ["T2", "T3"]),
    ]:
        bobj = next(x for x in gt["buildings"] if x["id"] == src_aid)
        pt = next(p for p in bobj["parts"] if p["osm_id"] == osm_part_id)
        poly = unary_union([rings_to_polygon(r) for r in pt["rings"]])
        tris = extrude_polygon_tris(poly, float(pt["z_min"]), float(pt["z_max"]))
        if builder.add_mesh(bnode, "architecture_opaque", tris, "MAT_BRIDGE_STEEL",
                            {**meta_base, "adjacent_blocks": pair, "osm_id": osm_part_id, "role": "level2_3_skybridge_link"}):
            building_components_map[src_aid].append(bnode)

    glb_bytes = builder.to_glb()
    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    OUT_GLB.write_bytes(glb_bytes)

    # -----------------------------------------------------------------------
    # Compute Sharp Feature Edges Display GLB (34-degree creases + boundaries)
    # -----------------------------------------------------------------------
    v89_doc, v89_bin = unpack_glb(glb_bytes)
    node_map = {n["name"]: n for n in v89_doc["nodes"] if "mesh" in n and "name" in n}

    def sharp_edges_for(names: list[str], threshold_deg: float = 34.0) -> np.ndarray:
        normals = []
        emap = defaultdict(list)
        for nm in names:
            tris = extract_source_tris(v89_doc, v89_bin, nm)
            for face in tris:
                nrm = np.cross(face[1] - face[0], face[2] - face[0])
                ln = np.linalg.norm(nrm)
                if ln < 1e-8:
                    continue
                nrm /= ln
                f_idx = len(normals)
                normals.append(nrm)
                for a_i, b_i in ((0, 1), (1, 2), (2, 0)):
                    p1 = tuple(np.round(face[a_i], 3))
                    p2 = tuple(np.round(face[b_i], 3))
                    if p1 == p2:
                        continue
                    emap[tuple(sorted((p1, p2)))].append(f_idx)
        thr = math.cos(math.radians(threshold_deg))
        segs = []
        for edge, faces in sorted(emap.items()):
            if len(faces) == 1 or min(float(np.dot(normals[faces[0]], normals[k])) for k in faces[1:]) < thr:
                segs.extend(edge)
        return np.asarray(segs, dtype="<f4").reshape(-1, 3)

    fam_colors = {"T": (0.93, 0.74, 0.45), "V": (0.85, 0.55, 0.35), "D": (0.50, 0.78, 0.75), "LRC": (0.98, 0.98, 0.91), "OTHER": (0.75, 0.82, 0.88)}
    fam_groups = defaultdict(list)
    for bldg in gt["buildings"]:
        fam_groups[bldg["family"]].extend(building_components_map[bldg["id"]])

    edge_doc = {
        "asset": {"version": "2.0", "generator": "BNBU v89 architectural sharp crease overlay"},
        "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [], "bufferViews": [], "accessors": [],
    }
    edge_bin = bytearray()
    edge_stats = {}
    for fam in ("T", "V", "D", "LRC", "OTHER"):
        ar = sharp_edges_for(fam_groups[fam])
        raw = ar.tobytes()
        off = len(edge_bin)
        edge_bin.extend(raw)
        edge_bin.extend(b"\0" * ((-len(edge_bin)) % 4))
        bv = len(edge_doc["bufferViews"])
        edge_doc["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(raw), "target": 34962})
        acc = len(edge_doc["accessors"])
        edge_doc["accessors"].append({
            "bufferView": bv, "componentType": 5126, "count": len(ar), "type": "VEC3",
            "min": ar.min(axis=0).astype(float).tolist(), "max": ar.max(axis=0).astype(float).tolist(),
        })
        mat_i = len(edge_doc["materials"])
        col = fam_colors[fam]
        edge_doc["materials"].append({
            "name": f"v89_{fam}_edges", "doubleSided": True, "alphaMode": "BLEND",
            "pbrMetallicRoughness": {"baseColorFactor": [*col, 0.70], "metallicFactor": 0, "roughnessFactor": 1},
        })
        m_i = len(edge_doc["meshes"])
        edge_doc["meshes"].append({
            "name": f"BNBU_V89_EDGES_{fam}",
            "primitives": [{"attributes": {"POSITION": acc}, "mode": 1, "material": mat_i}],
            "extras": {"displayOnly": True, "bird_collision_area_eligible": False},
        })
        n_i = len(edge_doc["nodes"])
        edge_doc["nodes"].append({"name": f"BNBU_V89_EDGES_{fam}", "mesh": m_i})
        edge_doc["scenes"][0]["nodes"].append(n_i)
        edge_stats[fam] = {"component_meshes": len(fam_groups[fam]), "sharp_edge_segments": int(len(ar) // 2)}
    edge_doc["buffers"] = [{"byteLength": len(edge_bin)}]
    OUT_EDGES.write_bytes(pack_glb(edge_doc, bytes(edge_bin)))

    # -----------------------------------------------------------------------
    # Quantitative Before vs After Audit + Registry + GIS GeoJSON + Atlas
    # -----------------------------------------------------------------------
    def footprint_of_glb(doc_x, bin_x, names):
        polys = []
        nmap_x = {n["name"]: n for n in doc_x["nodes"] if "mesh" in n and "name" in n}
        for nm in names:
            if nm not in nmap_x:
                continue
            tris = extract_source_tris(doc_x, bin_x, nm)
            for t in tris:
                p = Polygon([(t[0, 0], t[0, 1]), (t[1, 0], t[1, 1]), (t[2, 0], t[2, 1])])
                if p.is_valid and p.area > 1e-4:
                    polys.append(p)
        if not polys:
            return Polygon()
        u = unary_union(polys)
        return u.buffer(0) if not u.is_valid else u

    def obb_angle(poly):
        if poly.is_empty:
            return 0.0
        coords = list(poly.minimum_rotated_rectangle.exterior.coords)[:4]
        e1 = np.array(coords[1]) - np.array(coords[0])
        e2 = np.array(coords[2]) - np.array(coords[1])
        v = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
        return math.degrees(math.atan2(v[1], v[0])) % 180.0

    # Load v76/v88 baseline component lists for before/after delta measurement
    v76_atlas = json.loads((DATA / "BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json").read_text(encoding="utf-8"))
    old_comp_lookup = {r["id"]: r["existing_component_names"] for r in v76_atlas["building_records"]}
    # Add v88 extended names
    for aid, anc in [
        ("T29", [n["name"] for n in src_doc["nodes"] if "T29" in n.get("name", "") and "mesh" in n]),
        ("ADMIN", [n["name"] for n in src_doc["nodes"] if "_ADMIN" in n.get("name", "") and "mesh" in n]),
        ("HALL", [n["name"] for n in src_doc["nodes"] if "_HALL" in n.get("name", "") and "mesh" in n]),
        ("SPORT", [n["name"] for n in src_doc["nodes"] if "_SPORT" in n.get("name", "") and "mesh" in n and "SPORTS_PARK" not in n.get("name", "")]),
        ("THEATRE", [n["name"] for n in src_doc["nodes"] if "_THEATRE" in n.get("name", "") and "mesh" in n]),
        ("CC", [n["name"] for n in src_doc["nodes"] if n.get("name", "").endswith("_CC") or "_CC_" in n.get("name", "")]),
        ("YUZHAN", [n["name"] for n in src_doc["nodes"] if "_YUZHAN" in n.get("name", "") and "mesh" in n]),
        ("P2_CIRCULAR_COMMONS", [n["name"] for n in src_doc["nodes"] if "V24_P2_CIRCULAR_COMMONS_" in n.get("name", "")]),
    ]:
        old_comp_lookup[aid] = anc

    audit_rows = []
    building_records = []
    extended_records = []
    registry_assets = []
    geojson_features = []

    walk_road_polys = [road_poly, walk_poly]
    lake_polys = [(w["name"], unary_union([rings_to_polygon(r) for r in w["rings"]])) for w in gt["waters"]]

    for idx_b, bldg in enumerate(gt["buildings"]):
        aid = bldg["id"]
        fam = bldg["family"]
        gt_fp = unary_union([rings_to_polygon(r) for r in bldg["footprint_rings"]])
        new_fp = footprint_of_glb(v89_doc, v89_bin, building_components_map[aid])
        old_fp = footprint_of_glb(src_doc, src_bin, old_comp_lookup.get(aid, []))

        new_iou = float(new_fp.intersection(gt_fp).area / new_fp.union(gt_fp).area) if not new_fp.is_empty else 0.0
        new_dx = float(new_fp.centroid.x - gt_fp.centroid.x) if not new_fp.is_empty else 0.0
        new_dy = float(new_fp.centroid.y - gt_fp.centroid.y) if not new_fp.is_empty else 0.0
        new_err = math.hypot(new_dx, new_dy)

        if not old_fp.is_empty:
            old_iou = float(old_fp.intersection(gt_fp).area / old_fp.union(gt_fp).area)
            old_err = math.hypot(old_fp.centroid.x - gt_fp.centroid.x, old_fp.centroid.y - gt_fp.centroid.y)
            old_dang = ((obb_angle(old_fp) - obb_angle(gt_fp) + 90) % 180) - 90
        else:
            old_iou, old_err, old_dang = 0.0, None, None

        new_dang = ((obb_angle(new_fp) - obb_angle(gt_fp) + 90) % 180) - 90
        z_vals = [float(p["z_min"]) for p in bldg["parts"]] + [float(p["z_max"]) for p in bldg["parts"]]
        z_range = [round(min(z_vals), 2), round(max(z_vals), 2)]
        bx0, by0, bx1, by1 = gt_fp.bounds
        utm_bbox = [round(bx0 + OFFSET_X, 3), round(by0 + OFFSET_Y, 3), round(bx1 + OFFSET_X, 3), round(by1 + OFFSET_Y, 3)]

        # Proximity to roads, walkways & nearest lake (strictly planar reference, not entrance certification)
        d_road = round(float(new_fp.distance(road_poly)), 2)
        d_walk = round(float(new_fp.distance(walk_poly)), 2)
        lakes_dist = sorted((round(float(new_fp.distance(lp)), 2), lnm) for lnm, lp in lake_polys)

        anchor_nm = bldg["anchor_node"]
        if anchor_nm not in building_components_map[aid] and building_components_map[aid]:
            anchor_nm = building_components_map[aid][0]

        rec = {
            "id": aid, "family": fam, "display_label": bldg["display_label"],
            "source_anchor_node": anchor_nm,
            "existing_component_names": building_components_map[aid],
            "existing_component_count": len(building_components_map[aid]),
            "source_plan_area_sq_model_units": round(float(new_fp.area), 2),
            "source_bbox_utm_xy": utm_bbox,
            "source_mesh_z_range": z_range,
            "nearest_walk_or_road": [
                {"node": "V89_CAMPUS_PEDESTRIAN_WALKWAYS", "xy_gap_model_units": d_walk},
                {"node": "V89_CAMPUS_VEHICLE_ROADS_NETWORK", "xy_gap_model_units": d_road},
            ],
            "nearest_lake": [{"node": lnm, "xy_gap_model_units": d} for d, lnm in lakes_dist[:2]],
            "layout_iou_before_v88": round(old_iou, 3),
            "layout_iou_after_v89": round(new_iou, 3),
            "centroid_err_before_m": round(old_err, 2) if old_err is not None else None,
            "centroid_err_after_m": round(new_err, 2),
            "angle_err_before_deg": round(old_dang, 1) if old_dang is not None else None,
            "angle_err_after_deg": round(new_dang, 1),
            "no_measured_entry_doors": True, "no_photo_registered_windows": True,
            "not_proof_of_accessible_connection": True,
            "notes": "Layout corrected to 2025-06-10 WorldView-2 & OSM footprints; glass & entry doors remain unsurveyed.",
        }
        if fam in ("T", "V", "D", "LRC"):
            building_records.append(rec)
        else:
            extended_records.append(rec)

        audit_rows.append({
            "id": aid, "family": fam,
            "before_iou": rec["layout_iou_before_v88"], "after_iou": rec["layout_iou_after_v89"],
            "before_centroid_err_m": rec["centroid_err_before_m"], "after_centroid_err_m": rec["centroid_err_after_m"],
            "before_angle_err_deg": rec["angle_err_before_deg"], "after_angle_err_deg": rec["angle_err_after_deg"],
            "footprint_area_m2": round(float(gt_fp.area), 1), "z_max_m": z_range[1],
        })

        registry_assets.append({
            "index": idx_b, "id": aid, "family": fam,
            "record_group": "core_30" if fam in ("T", "V", "D", "LRC") else "extended_mapped",
            "display_label": bldg["display_label"], "source_anchor_node": anchor_nm,
            "existing_component_count": len(building_components_map[aid]),
            "source_mesh_z_range": z_range, "source_bbox_utm_xy": utm_bbox,
            "iou_before": rec["layout_iou_before_v88"], "iou_after": rec["layout_iou_after_v89"],
            "is_surveyed": False, "birdstrike_area_eligible": False,
        })

        wgs_geom = transform(lambda x, y: TO_WGS(x + OFFSET_X, y + OFFSET_Y), gt_fp)
        geojson_features.append({
            "type": "Feature",
            "geometry": mapping(wgs_geom),
            "properties": {
                "building_id": aid, "family": fam, "display_label": bldg["display_label"],
                "render_model_node": anchor_nm, "feature_type": "building_footprint_v89",
                "evidence_source": "WV02_2025-06-10 + OSM_2026-11",
                "iou_before": rec["layout_iou_before_v88"], "iou_after": rec["layout_iou_after_v89"],
                "is_surveyed": False,
            },
        })

    # Add water & sports & road features to GeoJSON for 2D GIS viewer
    for wt in gt["waters"]:
        p = unary_union([rings_to_polygon(r) for r in wt["rings"]])
        geojson_features.append({
            "type": "Feature",
            "geometry": mapping(transform(lambda x, y: TO_WGS(x + OFFSET_X, y + OFFSET_Y), p)),
            "properties": {"render_model_node": wt["name"], "role": "water_existing_v44_not_surveyed", "feature_type": "water_verified_v89", "is_surveyed": 0},
        })
    geojson_features.append({
        "type": "Feature",
        "geometry": mapping(transform(lambda x, y: TO_WGS(x + OFFSET_X, y + OFFSET_Y), road_poly)),
        "properties": {"render_model_node": "V89_CAMPUS_VEHICLE_ROADS_NETWORK", "role": "vehicle_road", "is_surveyed": 0},
    })
    geojson_features.append({
        "type": "Feature",
        "geometry": mapping(transform(lambda x, y: TO_WGS(x + OFFSET_X, y + OFFSET_Y), walk_poly)),
        "properties": {"render_model_node": "V89_CAMPUS_PEDESTRIAN_WALKWAYS", "role": "footpath", "is_surveyed": 0},
    })

    # Write Atlas JSON
    atlas = {
        "version": "v89",
        "source": "Layout-corrected BNBU v89 built from 2025-06-10 WV02 + OSM 2026-11 + v71/v88 lakefront/terrain context",
        "building_count": len(building_records),
        "extended_count": len(extended_records),
        "total_mapped_assets": len(building_records) + len(extended_records),
        "active_mesh_nodes": len([n for n in v89_doc["nodes"] if "mesh" in n]),
        "active_triangles": int(sum(v89_doc["accessors"][v89_doc["meshes"][n["mesh"]]["primitives"][0]["indices"]]["count"] // 3
                                    for n in v89_doc["nodes"] if "mesh" in n)),
        "families": {
            "T": {"source_building_count": 8, "building_ids": [f"T{i}" for i in range(1, 9)]},
            "V": {"source_building_count": 15, "building_ids": [f"V{i}" for i in range(15, 30)]},
            "D": {"source_building_count": 6, "building_ids": [f"D{i}" for i in range(1, 7)]},
            "LRC": {"source_building_count": 1, "building_ids": ["LRC"]},
            "OTHER": {"source_building_count": len(extended_records), "building_ids": [r["id"] for r in extended_records]},
        },
        "feature_edge_overlay": edge_stats,
        "building_records": building_records,
        "extended_records": extended_records,
        "phaseII_network_disconnection_audit": [],
        "quarantined_hypotheses": ["CTV_SMALL_HOUSE"],
        "new_surveyed_glazing_area": 0,
        "window_panel_count_measured": None,
        "blender_compatible": True,
        "has_vertex_normals": True,
        "glb_sha256": sha256_bytes(glb_bytes),
    }
    OUT_ATLAS.write_text(json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write GeoJSON
    OUT_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": geojson_features}, ensure_ascii=False), encoding="utf-8")

    # Write Audit JSON
    ious_b = [r["before_iou"] for r in audit_rows if r["before_centroid_err_m"] is not None]
    ious_a = [r["after_iou"] for r in audit_rows]
    audit_report = {
        "version": "v89",
        "issue": "#13",
        "reference_imagery": gt["reference_imagery"],
        "summary": {
            "buildings_evaluated": len(audit_rows),
            "mean_iou_before_v88": round(float(np.mean(ious_b)), 3),
            "mean_iou_after_v89": round(float(np.mean(ious_a)), 3),
            "min_iou_after_v89": round(float(min(ious_a)), 3),
            "active_mesh_nodes": atlas["active_mesh_nodes"],
            "active_triangles": atlas["active_triangles"],
            "glb_bytes": len(glb_bytes),
            "glb_sha256": atlas["glb_sha256"],
        },
        "buildings": audit_rows,
    }
    OUT_AUDIT.write_text(json.dumps(audit_report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write Registry JSON & CSV
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REG_JSON.write_text(json.dumps({
        "version": "v89", "campus": "BNBU Zhuhai (Phase I + Phase II)",
        "mapped_assets": registry_assets,
        "quarantined_hypotheses": [{"id": "CTV_SMALL_HOUSE", "status": "quarantined_unverified"}],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT_REG_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["index", "id", "family", "record_group", "display_label",
                                          "source_anchor_node", "existing_component_count", "iou_before", "iou_after"])
        w.writeheader()
        for row in registry_assets:
            w.writerow({k: row[k] for k in w.fieldnames})

    return audit_report["summary"]


if __name__ == "__main__":
    summary = build()
    print(json.dumps(summary, indent=2))
