"""Summarize reviewed pane vegetation, view masks and observed approach routes."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from math import hypot, isfinite
from pathlib import Path

from .evidence import EvidenceTier
from .pane_registry import PaneIdentity, PaneRegistry
from .vegetation import VEGETATION_BUFFERS
from .vegetation_segmentation import DEFAULT_CLASSES, summarize_class_mask


_ANNULAR_RADII_M = (0, 5, 25, 100, 1000, 10000)
_VIEW_CLASSES = {
    "reflected_vegetation", "reflected_other", "transmitted_vegetation",
    "transmitted_other", "other_visible",
}
_UNRESOLVED_PIXELS = {"outside", "occluded", "unclassified"}
_SITE_RANGES = {
    "facade_tree_cover_50m_percent": 100,
    "facade_porous_cover_50m_percent": 100,
    "nearest_crown_distance_m": 100000,
    "canopy_height_m": 200,
    "pane_sill_height_m": 1000,
    "corridor_obstruction_share": 1,
}


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value


def _number(value, label, *, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError(f"{label} must be in [{minimum}, {maximum}]")
    return value


def _timestamp(value, label):
    try:
        timestamp = datetime.fromisoformat(_text(value, label))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 timestamp with a UTC offset") from exc
    if timestamp.utcoffset() is None:
        raise ValueError(f"{label} must be an ISO 8601 timestamp with a UTC offset")
    return timestamp


def _point(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must be an [x, y] pair in metres")
    return tuple(_number(coordinate, label) for coordinate in value)


def _quality(row, label):
    """Keep QA and source metadata while omitting unreviewed numeric values."""
    if row is None:
        return {
            "status": "missing",
            "reason": f"No {label} record supplied",
            "review_action": f"Collect and review a {label} source for this pane",
        }
    status = row.get("status")
    if status not in {"reviewed", "pending", "rejected", "missing"}:
        raise ValueError(f"{label} status must be reviewed, pending, rejected or missing")
    result = {
        "status": status,
        "source_id": row.get("source_id"),
        "source_ref": row.get("source_ref"),
        "recorded_at": row.get("recorded_at"),
        "evidence_tier": EvidenceTier(row.get("evidence_tier", "unknown")).value,
    }
    if status != "missing":
        _text(result["source_id"], f"{label}.source_id")
        _text(result["source_ref"], f"{label}.source_ref")
        _timestamp(result["recorded_at"], f"{label}.recorded_at")
    elif result["recorded_at"] is not None:
        _timestamp(result["recorded_at"], f"{label}.recorded_at")
    if status == "reviewed":
        if result["evidence_tier"] == "unknown":
            raise ValueError(f"Reviewed {label} requires an evidence tier")
        result["reviewer_id"] = _text(row.get("reviewer_id"), f"{label}.reviewer_id")
        result["annotation_version"] = _text(
            row.get("annotation_version"), f"{label}.annotation_version"
        )
    else:
        result["reason"] = _text(row.get("reason"), f"{label}.reason")
        result["review_action"] = _text(
            row.get("review_action", f"Review or replace the {label} source"), f"{label}.review_action"
        )
    return result


def _mask_inputs(mask, classes):
    if not mask or not mask[0]:
        raise ValueError("A reviewed mask must contain pixels")
    if any(len(row) != len(mask[0]) for row in mask):
        raise ValueError("A reviewed mask must be rectangular")
    counts = Counter(label for row in mask for label in row)
    unknown = set(counts) - (classes | _UNRESOLVED_PIXELS)
    if unknown:
        raise ValueError(f"Unknown mask labels: {sorted(unknown)}")
    valid = [[label in classes for label in row] for row in mask]
    footprint_pixels = sum(counts.values()) - counts["outside"]
    pixel_audit = {
        "footprint_pixels": footprint_pixels,
        "valid_pixels": footprint_pixels - counts["occluded"] - counts["unclassified"],
        "occluded_pixels": counts["occluded"],
        "unclassified_pixels": counts["unclassified"],
    }
    return counts, valid, pixel_audit


def _ring(row, band, radii_m, center, resolution):
    if row is None or row.get("mask") is None:
        reason = row.get("reason") if row is not None else "No mask supplied"
        return {
            "status": "missing",
            "reason": _text(reason, f"{band}.reason"),
            "review_action": "Supply a clipped mask for this annulus and review its labels",
        }
    origin = _point(row.get("upper_left_pixel_center_xy_m"), f"{band}.upper_left_pixel_center_xy_m")
    mask = row["mask"]
    _, valid, pixel_audit = _mask_inputs(mask, DEFAULT_CLASSES)
    inner, outer = radii_m
    for row_index, cells in enumerate(mask):
        for col_index, label in enumerate(cells):
            if label == "outside":
                continue
            x = origin[0] + col_index * resolution
            y = origin[1] - row_index * resolution
            distance = hypot(x - center[0], y - center[1])
            if not inner <= distance < outer:
                raise ValueError(f"Mask for {band} contains a pixel outside its annulus")
    area = resolution ** 2
    audit = {
        **pixel_audit,
        "upper_left_pixel_center_xy_m": origin,
        "footprint_area_m2": pixel_audit["footprint_pixels"] * area,
        "valid_area_m2": pixel_audit["valid_pixels"] * area,
        "occluded_area_m2": pixel_audit["occluded_pixels"] * area,
        "unclassified_area_m2": pixel_audit["unclassified_pixels"] * area,
    }
    if not pixel_audit["valid_pixels"]:
        return {
            "status": "missing",
            "reason": "No interpretable mask pixels",
            "review_action": "Check the raster registration and use clearer imagery",
            **audit,
        }
    summary = summarize_class_mask(mask, valid_mask=valid, pixel_area_m2=area)
    cover_error = row.get("cover_uncertainty_pp")
    return {
        "status": "reviewed",
        **audit,
        "tree_canopy_cover_percent": summary["tree_canopy_cover_percent"],
        "class_cover_percent": summary["class_cover_percent"],
        "cover_uncertainty_pp": None if cover_error is None else _number(
            cover_error, f"{band}.cover_uncertainty_pp", minimum=0, maximum=100
        ),
        "uncertainty_missing_reason": _text(
            row.get("uncertainty_missing_reason"), f"{band}.uncertainty_missing_reason"
        ) if cover_error is None else None,
    }


def _land_cover(row):
    evidence = _quality(row, "land-cover")
    if evidence["status"] != "reviewed":
        missing = {key: evidence[key] for key in ("reason", "review_action")}
        return {
            **evidence,
            "bands": {band: {"status": "missing", **missing} for band in VEGETATION_BUFFERS},
        }
    center = _point(row.get("center_xy_m"), "land_cover.center_xy_m")
    resolution = _number(row.get("pixel_resolution_m"), "land_cover.pixel_resolution_m", minimum=0)
    pixel_area = resolution * resolution
    if pixel_area == 0 or not isfinite(pixel_area):
        raise ValueError("land_cover.pixel_resolution_m must produce a finite positive pixel area")
    bands = row.get("bands", {})
    unknown = set(bands) - set(VEGETATION_BUFFERS)
    if unknown:
        raise ValueError(f"Unknown annular bands: {sorted(unknown)}")
    return {
        **evidence,
        "crs": _text(row.get("crs"), "land_cover.crs"),
        "position_reference": _text(row.get("position_reference"), "land_cover.position_reference"),
        "center_xy_m": center,
        "season": _text(row.get("season"), "land_cover.season"),
        "pixel_resolution_m": resolution,
        "bands": {
            band: _ring(bands.get(band), band, radii, center, resolution)
            for band, radii in zip(VEGETATION_BUFFERS, zip(_ANNULAR_RADII_M, _ANNULAR_RADII_M[1:]))
        },
    }


def _site_context(row):
    evidence = _quality(row, "site-context")
    values = {}
    for field, maximum in _SITE_RANGES.items():
        value = row.get(field) if evidence["status"] == "reviewed" else None
        values[field] = None if value is None else _number(value, field, minimum=0, maximum=maximum)
    resource_note = row.get("resource_attraction_note") if evidence["status"] == "reviewed" else None
    return {
        **evidence,
        **values,
        "resource_attraction_note": _text(resource_note, "resource_attraction_note")
        if resource_note is not None else None,
    }


def _bearing(value, label):
    bearing = _number(value, label, minimum=0, maximum=360)
    if bearing == 360:
        raise ValueError(f"{label} must be less than 360 degrees")
    return bearing


def _reflection(row):
    evidence = _quality(row, "reflection")
    result = {
        **evidence,
        "view_id": _text(row.get("view_id"), "reflection.view_id"),
        "approach_bearing_deg": _bearing(row.get("approach_bearing_deg"), "reflection.approach_bearing_deg"),
        "light_conditions": _text(row.get("light_conditions"), "reflection.light_conditions"),
        "reflected_vegetation_share": None,
    }
    if evidence["status"] != "reviewed":
        return result
    counts, _, audit = _mask_inputs(row.get("mask"), _VIEW_CLASSES)
    result.update(audit)
    valid_pixels = audit["valid_pixels"]
    if not valid_pixels:
        return {
            **result,
            "status": "missing",
            "reason": "No interpretable glass pixels",
            "review_action": "Recheck the pane crop or repeat the same view under usable light",
        }
    return {
        **result,
        "interpretable_share": valid_pixels / audit["footprint_pixels"],
        "reflected_vegetation_share": counts["reflected_vegetation"] / valid_pixels,
        "transmitted_vegetation_share": counts["transmitted_vegetation"] / valid_pixels,
        "view_class_pixel_counts": {label: counts[label] for label in sorted(_VIEW_CLASSES)},
    }


def _route(row, starts_at, ends_at):
    time = _timestamp(row.get("observed_at"), "route.observed_at")
    if not starts_at <= time < ends_at:
        raise ValueError("route.observed_at must fall within its monitoring session")
    return {
        "track_id": _text(row.get("track_id"), "route.track_id"),
        "track_ref": _text(row.get("track_ref"), "route.track_ref"),
        "observed_at": row["observed_at"],
        "species_or_guild": _text(row.get("species_or_guild"), "route.species_or_guild"),
        "approach_bearing_deg": _bearing(row.get("approach_bearing_deg"), "route.approach_bearing_deg"),
    }


def _session(row):
    evidence = _quality(row, "monitoring-session")
    result = {
        **evidence,
        "session_id": _text(row.get("session_id"), "session.session_id"),
        "effort_s": None,
        "observed_route_count": None,
        "routes": [],
    }
    if evidence["status"] != "reviewed":
        return result
    start = _timestamp(row.get("starts_at"), "session.starts_at")
    end = _timestamp(row.get("ends_at"), "session.ends_at")
    duration = (end - start).total_seconds()
    if duration <= 0:
        raise ValueError("Monitoring session must end after it starts")
    mode = row.get("coverage_mode")
    if mode not in {"continuous", "selected"}:
        raise ValueError("session.coverage_mode must be continuous or selected")
    effort = _number(row.get("effort_s"), "session.effort_s", minimum=0, maximum=duration)
    if effort == 0 or (mode == "continuous" and effort != duration):
        raise ValueError("Review needs positive effort; a continuous session cannot contain gaps")
    if "routes" not in row:
        raise ValueError("Reviewed sessions require an explicit routes list")
    routes = [_route(route, start, end) for route in row["routes"]]
    return {
        **result,
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "coverage_mode": mode,
        "effort_s": effort,
        "phenology": _text(row.get("phenology"), "session.phenology"),
        "weather": _text(row.get("weather"), "session.weather"),
        "observed_route_count": len(routes) if mode == "continuous" or routes else None,
        "routes": sorted(routes, key=lambda route: route["track_id"]),
    }


def _unique_ids(rows, id_key):
    if len({row[id_key] for row in rows}) != len(rows):
        raise ValueError(f"Duplicate {id_key} in vegetation bundle")


def _record_for_pane(row, subject):
    if row is not None and PaneIdentity(**row["pane"]) != subject:
        raise ValueError("Vegetation record pane identity does not match the bundle")
    return row


def summarize_pane_vegetation(bundle, *, registry: PaneRegistry | None = None):
    """Summarize one exact pane, keeping site, optical and route evidence separate.

    Field data must reference a physically verified pane in the supplied
    registry. Data recorded on different dates remain separate; the report
    does not assign a view to a route simply because their bearings agree.
    """
    pane = PaneIdentity(**bundle["pane"])
    kind = bundle["dataset_kind"]
    if kind not in {"field", "synthetic"}:
        raise ValueError("dataset_kind must be field or synthetic")
    if registry is not None:
        if registry.dataset_kind != kind:
            raise ValueError("Vegetation and registry dataset_kind must match")
        registry.require(pane, field_verified=kind == "field")
    elif kind == "field":
        raise ValueError("Field vegetation requires a field-verified pane registry")

    land = _land_cover(_record_for_pane(bundle.get("land_cover"), pane))
    site = _site_context(_record_for_pane(bundle.get("site_context"), pane))
    views = [_reflection(_record_for_pane(row, pane)) for row in bundle.get("reflections", [])]
    sessions = [_session(_record_for_pane(row, pane)) for row in bundle.get("monitoring", [])]
    _unique_ids(views, "view_id")
    _unique_ids(sessions, "session_id")
    _unique_ids([route for session in sessions for route in session["routes"]], "track_id")
    return {
        "pane": pane.as_dict(),
        "dataset_kind": kind,
        "land_cover": land,
        "site_context": site,
        "reflection_views": sorted(views, key=lambda view: view["view_id"]),
        "approach_monitoring": sorted(sessions, key=lambda session: session["session_id"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Pane vegetation evidence JSON")
    parser.add_argument("--registry", type=Path, help="Pane registry JSON (required for field data)")
    parser.add_argument("--output", type=Path, help="Write JSON to a file instead of stdout")
    args = parser.parse_args()
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        registry = (
            PaneRegistry.from_dict(json.loads(args.registry.read_text(encoding="utf-8")))
            if args.registry else None
        )
        result = summarize_pane_vegetation(bundle, registry=registry)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
