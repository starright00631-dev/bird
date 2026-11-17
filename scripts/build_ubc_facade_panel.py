#!/usr/bin/env python3
"""Build a validated canonical facade-date panel from Zulian et al. (2023)."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.inspect_zulian_appendix import EXPECTED_SHA256, inspect_appendix

SOURCE_FIELDS = {
    "survey_date": "SURVEY_DATE", "season": "SEASON",
    "building_id": "BUILDING_X", "facade_label": "FACADE", "method_code": "METHOD",
    "mortality_count": "COLLISIONMORTALITY_X", "other_collision_count": "COLLISIONS_X",
    "facade_area_m2": "FACADE_AREA", "glass_area_m2": "AREA_GLASS",
    "facade_porous_cover_percent": "PERC_VEG_AND_POROUS_SURFACE_FACADE",
    "facade_tree_cover_percent": "TREECOVER_FACADE_PERCENT",
    "stories_reflecting_canopy": "STORIES_REFLECT_CANOPY",
    "building_vegetation_proportion": "VEGE_PERC", "building_storeys": "STOREYS",
    "facade_direction": "DIRECTION", "facade_orientation_angle_degrees": "ANGLE_FROM_LINEAR_DIR_MEAN",
}
PANEL_FIELDS = [
    "source_row", "survey_date", "season", "building_id", "facade_label", "facade_id",
    "method_code", "survey_hours", "mortality_count", "mortality_present",
    "other_collision_count", "other_collision_present", "facade_area_m2", "glass_area_m2",
    "glass_fraction", "facade_porous_cover_percent", "facade_tree_cover_percent",
    "stories_reflecting_canopy", "building_vegetation_proportion", "building_storeys",
    "facade_direction", "facade_orientation_angle_degrees",
]


def _number(row, source_field, row_number):
    value = (row.get(source_field) or "").strip()
    if not value:
        raise ValueError(f"Missing {source_field} at source row {row_number}")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric {source_field}={value!r} at row {row_number}") from exc
    if not (number == number and abs(number) != float("inf")):
        raise ValueError(f"Non-finite {source_field} at source row {row_number}")
    return number


def build_panel(raw: bytes, *, strict_source: bool = True):
    source_audit = inspect_appendix(raw, strict=strict_source)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    rows = list(reader)
    panel, seen, static_by_facade, building_vegetation = [], set(), {}, {}
    method_counts, season_counts = Counter(), Counter()
    for row_number, row in enumerate(rows, start=2):
        source = {key: row.get(value, "") for key, value in SOURCE_FIELDS.items()}
        raw_date = source["survey_date"].strip()
        try:
            survey_date = date.fromisoformat(raw_date).isoformat()
        except ValueError:
            survey_date = None
            for date_format in ("%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
                try:
                    survey_date = datetime.strptime(raw_date, date_format).date().isoformat()
                    break
                except ValueError:
                    continue
            if survey_date is None:
                raise ValueError(f"Unsupported SURVEY_DATE={raw_date!r} at source row {row_number}")
        season = source["season"].strip().lower()
        if season not in {"fall", "winter", "spring", "summer"}:
            raise ValueError(f"Unknown SEASON={season!r} at source row {row_number}")
        building, facade = source["building_id"].strip(), source["facade_label"].strip()
        facade_id = f"{building}::{facade}"
        key = (building, facade, survey_date)
        if key in seen:
            raise ValueError(f"Duplicate facade-date key at source row {row_number}: {key}")
        seen.add(key)
        method_value = _number(row, SOURCE_FIELDS["method_code"], row_number)
        if not method_value.is_integer():
            raise ValueError(f"Non-integer METHOD={method_value} at source row {row_number}")
        method = int(method_value)
        if method not in {1, 2}:
            raise ValueError(f"Unexpected METHOD={method} at source row {row_number}")
        survey_hours = 24 * method
        mortality_count = _number(row, SOURCE_FIELDS["mortality_count"], row_number)
        other_count = _number(row, SOURCE_FIELDS["other_collision_count"], row_number)
        if mortality_count < 0 or other_count < 0 or mortality_count != int(mortality_count) or other_count != int(other_count):
            raise ValueError(f"Invalid collision count at source row {row_number}")
        values = {
            "facade_area_m2": _number(row, SOURCE_FIELDS["facade_area_m2"], row_number),
            "glass_area_m2": _number(row, SOURCE_FIELDS["glass_area_m2"], row_number),
            "facade_porous_cover_percent": _number(row, SOURCE_FIELDS["facade_porous_cover_percent"], row_number),
            "facade_tree_cover_percent": _number(row, SOURCE_FIELDS["facade_tree_cover_percent"], row_number),
            "stories_reflecting_canopy": _number(row, SOURCE_FIELDS["stories_reflecting_canopy"], row_number),
            "building_vegetation_proportion": _number(row, SOURCE_FIELDS["building_vegetation_proportion"], row_number),
            "building_storeys": _number(row, SOURCE_FIELDS["building_storeys"], row_number),
            "facade_direction": source["facade_direction"].strip().lower(),
            "facade_orientation_angle_degrees": _number(row, SOURCE_FIELDS["facade_orientation_angle_degrees"], row_number),
        }
        if values["facade_area_m2"] <= 0:
            raise ValueError(f"Non-positive facade area at source row {row_number}")
        if values["glass_area_m2"] < 0 or values["glass_area_m2"] > values["facade_area_m2"]:
            raise ValueError(f"Glass area outside [0, facade area] at source row {row_number}")
        for feature in ("facade_porous_cover_percent", "facade_tree_cover_percent"):
            if not 0 <= values[feature] <= 100:
                raise ValueError(f"{feature} outside [0,100] at source row {row_number}")
        if not 0 <= values["building_vegetation_proportion"] <= 1:
            raise ValueError(f"Building vegetation proportion outside [0,1] at row {row_number}")
        if values["stories_reflecting_canopy"] < 0 or values["building_storeys"] < 0:
            raise ValueError(f"Negative story count at source row {row_number}")
        if not values["stories_reflecting_canopy"].is_integer():
            raise ValueError(
                f"Non-integer stories_reflecting_canopy at source row {row_number}"
            )
        if not 0 <= values["facade_orientation_angle_degrees"] <= 360:
            raise ValueError(f"Facade orientation angle outside [0,360] at source row {row_number}")
        previous_building_veg = building_vegetation.setdefault(building, values["building_vegetation_proportion"])
        if previous_building_veg != values["building_vegetation_proportion"]:
            raise ValueError(f"Building-level VEGE_PERC changes within {building}")
        previous = static_by_facade.setdefault(facade_id, values)
        if previous != values:
            raise ValueError(f"Facade-static predictors change across visits for {facade_id}")
        panel.append({
            "source_row": row_number, "survey_date": survey_date, "season": season,
            "building_id": building, "facade_label": facade, "facade_id": facade_id,
            "method_code": method, "survey_hours": survey_hours,
            "mortality_count": int(mortality_count), "mortality_present": int(mortality_count > 0),
            "other_collision_count": int(other_count), "other_collision_present": int(other_count > 0),
            **values, "glass_fraction": values["glass_area_m2"] / values["facade_area_m2"],
        })
        method_counts[str(method)] += 1
        season_counts[season] += 1
    if strict_source:
        if len(panel) != 8835 or len(static_by_facade) != 57 or len(building_vegetation) != 8:
            raise ValueError("Canonical panel dimensions differ from pinned Appendix 1")
        if dict(method_counts) != {"1": 4845, "2": 3990}:
            raise ValueError(f"METHOD distribution changed: {dict(method_counts)}")
        if dict(season_counts) != {"fall": 1881, "winter": 3192, "spring": 1881, "summer": 1881}:
            raise ValueError(f"SEASON distribution changed: {dict(season_counts)}")
    panel.sort(key=lambda row: (row["survey_date"], row["building_id"], row["facade_label"]))
    audit = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_sha256_pinned": hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
        "rows": len(panel), "buildings": len({r["building_id"] for r in panel}),
        "facades": len(static_by_facade), "survey_dates": len({r["survey_date"] for r in panel}),
        "unique_facade_date_keys": len(seen), "duplicate_facade_date_keys": 0,
        "mortality_events": sum(r["mortality_count"] for r in panel),
        "positive_mortality_visits": sum(r["mortality_present"] for r in panel),
        "other_collision_events": sum(r["other_collision_count"] for r in panel),
        "positive_other_collision_visits": sum(r["other_collision_present"] for r in panel),
        "method_counts": dict(sorted(method_counts.items())),
        "season_counts": dict(sorted(season_counts.items())),
        "building_level_vegetation_proportion": building_vegetation,
        "feature_semantics": {
            "VEGE_PERC": "building-level proportion in [0,1]; not the facade-level VegPer predictor",
            "PERC_VEG_AND_POROUS_SURFACE_FACADE": "facade-level 50-m buffer porous/ground-shrub cover percent",
            "TREECOVER_FACADE_PERCENT": "facade-level tree canopy cover percent",
            "STORIES_REFLECT_CANOPY": "facade stories with glass and unobstructed adjacent canopy reflection",
            "METHOD": "1=24 hours, 2=48 hours; survey_hours is 24*METHOD",
        },
        "source_audit": source_audit,
        "interpretation_limits": [
            "Primary outcome is detected carcass presence, not true collision probability or detection-corrected mortality.",
            "Glass type/product category is not present; AREA_GLASS is glass area, not glass optical class.",
            "Only eight buildings from one temperate campus are represented.",
            "The separate De Groot raw collision file is not row-joined to this panel.",
        ],
    }
    return panel, audit


def write_panel(panel, csv_path, audit, audit_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PANEL_FIELDS)
        writer.writeheader()
        writer.writerows(panel)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/derived/ubc/zulian_appendix1.csv"))
    parser.add_argument("--panel-out", type=Path, default=Path("data/derived/ubc/ubc_facade_survey_panel.csv"))
    parser.add_argument("--audit-out", type=Path, default=Path("data/derived/ubc/ubc_facade_panel_audit.json"))
    parser.add_argument("--allow-unpinned", action="store_true")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    panel, audit = build_panel(raw, strict_source=not args.allow_unpinned)
    write_panel(panel, args.panel_out, audit, args.audit_out)
    print(json.dumps({
        "rows": audit["rows"], "buildings": audit["buildings"], "facades": audit["facades"],
        "survey_dates": audit["survey_dates"], "mortality_events": audit["mortality_events"],
        "positive_mortality_visits": audit["positive_mortality_visits"],
        "method_counts": audit["method_counts"], "season_counts": audit["season_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
