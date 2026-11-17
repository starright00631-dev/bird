#!/usr/bin/env python3
"""Capture and validate full OSM way geometry for BNBU T1-T3.

This script only writes a raw source snapshot and a provenance/status record.
It never edits the campus GLB, active GIS, or any physical geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference" / "v86_osm_way_snapshot.json"
DEFAULT_RAW = ROOT / "qa" / "v87_osm_full_geometry_live.json"
DEFAULT_STATUS = ROOT / "qa" / "v87_osm_geometry_status.json"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "BNBU-Campus-Research/0.87 (reproducible OSM building-footprint geometry capture; https://github.com/starright00631-dev/bird)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_expected(path: Path = REFERENCE) -> dict[str, dict[str, Any]]:
    doc = json.loads(path.read_text("utf-8"))
    ways = doc.get("ways")
    if not isinstance(ways, dict) or set(ways) != {"T1", "T2", "T3"}:
        raise ValueError("v86 source snapshot must contain exactly T1, T2 and T3 ways")
    out = {}
    for label, row in ways.items():
        nodes = row.get("nodes")
        if not isinstance(nodes, list) or len(nodes) < 4:
            raise ValueError(f"{label}: missing original OSM node reference sequence")
        out[label] = {
            "id": int(row["id"]),
            "name_en": row.get("tags", {}).get("name:en"),
            "nodes": [int(x) for x in nodes],
        }
    return out


def build_query(expected: dict[str, dict[str, Any]]) -> str:
    ids = ",".join(str(row["id"]) for row in expected.values())
    return f"[out:json][timeout:90];\nway(id:{ids});\nout meta geom;"


def validate_payload(payload: dict[str, Any], expected: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Validate shape and identity. Node-sequence changes are reported, not hidden."""
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise ValueError("Overpass response has no elements array")
    by_id = {(e.get("type"), int(e.get("id", -1))): e for e in elements if isinstance(e, dict)}
    summary: dict[str, Any] = {
        "geometry_ready": True,
        "registration_eligible": True,
        "way_count": 0,
        "ways": {},
        "blocking_reasons": [],
    }
    for label, exp in expected.items():
        key = ("way", exp["id"])
        if key not in by_id:
            raise ValueError(f"Missing expected OSM way {exp['id']} ({label})")
        way = by_id[key]
        nodes = [int(x) for x in way.get("nodes", [])]
        geom = way.get("geometry")
        tags = way.get("tags", {})
        if not isinstance(geom, list) or len(geom) < 4:
            raise ValueError(f"{label}: full geometry missing or too short")
        if len(nodes) != len(geom):
            raise ValueError(f"{label}: node/geometry length mismatch {len(nodes)} != {len(geom)}")
        coords = []
        for i, p in enumerate(geom):
            lon, lat = float(p["lon"]), float(p["lat"])
            if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError(f"{label}: invalid coordinate at vertex {i}")
            coords.append([lon, lat])
        if nodes[0] != nodes[-1]:
            raise ValueError(f"{label}: OSM way is not a closed ring")
        if abs(coords[0][0] - coords[-1][0]) > 1e-9 or abs(coords[0][1] - coords[-1][1]) > 1e-9:
            raise ValueError(f"{label}: first and last geometry coordinates do not close")
        if len(set(nodes[:-1])) < 3:
            raise ValueError(f"{label}: fewer than three unique boundary nodes")
        node_match = nodes == exp["nodes"]
        name_match = tags.get("name:en") == exp["name_en"]
        building_match = tags.get("building") == "university"
        if not node_match:
            summary["registration_eligible"] = False
            summary["blocking_reasons"].append(f"{label}: node reference sequence changed since v86 snapshot")
        if not name_match or not building_match:
            summary["registration_eligible"] = False
            summary["blocking_reasons"].append(f"{label}: building identity tags differ from v86 snapshot")
        summary["ways"][label] = {
            "way_id": exp["id"],
            "name_en": tags.get("name:en"),
            "osm_version": way.get("version"),
            "osm_timestamp": way.get("timestamp"),
            "node_count": len(nodes),
            "closed_ring": True,
            "node_sequence_matches_v86": node_match,
            "name_matches_v86": name_match,
            "building_tag_matches": building_match,
            "geometry_lon_lat": coords,
        }
        summary["way_count"] += 1
    if summary["way_count"] != len(expected):
        raise ValueError(f"Expected {len(expected)} validated ways")
    return summary


def fetch_payload(expected: dict[str, dict[str, Any]], max_retries: int = 2) -> tuple[dict[str, Any], str, str]:
    query = build_query(expected)
    errors = []
    session = requests.Session()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for endpoint in ENDPOINTS:
        for attempt in range(1, max_retries + 1):
            try:
                response = session.post(endpoint, data={"data": query}, headers=headers, timeout=(20, 120))
                response.raise_for_status()
                payload = response.json()
                validate_payload(payload, expected)
                return payload, endpoint, query
            except Exception as exc:  # try alternate public Overpass instances
                errors.append({"endpoint": endpoint, "attempt": attempt, "error": str(exc)[:500]})
                if attempt < max_retries:
                    time.sleep(min(5 * attempt, 15))
    raise RuntimeError("All Overpass endpoints failed: " + json.dumps(errors, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-output", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--status-output", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--input-json", type=Path, help="Validate a saved Overpass JSON response without network access")
    args = ap.parse_args()
    expected = load_expected()
    query = build_query(expected)
    if args.input_json:
        payload = json.loads(args.input_json.read_text("utf-8"))
        endpoint = "offline-input"
    else:
        payload, endpoint, query = fetch_payload(expected, args.max_retries)
    validation = validate_payload(payload, expected)
    raw_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    record = {
        "schema": "bnbu-v87-osm-full-way-geometry-v1",
        "retrieved_at_utc": utc_now(),
        "source": "OpenStreetMap Overpass API",
        "source_license": "Open Database License (ODbL)",
        "endpoint": endpoint,
        "query": query,
        "v86_source_snapshot": "2026-11-10T19:09:14Z",
        "v86_snapshot_file": "reference/v86_osm_way_snapshot.json",
        "raw_elements_sha256": raw_sha,
        "validation": validation,
        "elements": payload["elements"],
    }
    status = {
        "schema": "bnbu-v87-osm-geometry-status-v1",
        "retrieved_at_utc": record["retrieved_at_utc"],
        "endpoint": endpoint,
        "raw_elements_sha256": raw_sha,
        "geometry_ready": validation["geometry_ready"],
        "registration_eligible": validation["registration_eligible"],
        "way_count": validation["way_count"],
        "ways": validation["ways"],
        "blocking_reasons": validation["blocking_reasons"],
        "physical_master_modified": False,
        "active_gis_modified": False,
        "candidate_geometry_created": False,
        "notes": [
            "OSM ways are community-mapped footprints, not surveyed building control polygons.",
            "Full way geometry improves on out-center bbox centres but is not photogrammetric or geodetic survey evidence.",
            "No geometry is promoted into the scientific master by this acquisition step.",
        ],
    }
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.status_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_text(json.dumps(record, ensure_ascii=False, indent=2), "utf-8")
    args.status_output.write_text(json.dumps(status, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({"raw_output": str(args.raw_output), "status_output": str(args.status_output),
                      "raw_sha256": raw_sha, "registration_eligible": validation["registration_eligible"],
                      "blocking_reasons": validation["blocking_reasons"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)