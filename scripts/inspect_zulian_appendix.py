#!/usr/bin/env python3
"""Download, pin and audit the complete Zulian et al. (2023) survey panel.

Appendix 1 is not merely a 57-row covariate table: it contains 8,835 repeated
facade-date observations, the carcass-mortality outcome and facade-level
predictors. The panel is already at the correct survey grain, so it must not
be joined row-by-row to the separately versioned De Groot raw CSV.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://ace-eco.org/vol18/iss2/art15/appendix1.csv"
PAPER_DOI = "10.5751/ACE-02482-180215"
EXPECTED_SHA256 = "0baba75389249af1dad546868183f956dd38facef64ae35b04ab761e293fd8a7"
EXPECTED_ROWS = 8835
EXPECTED_COLUMNS = 45
EXPECTED_FACADES = 57
EXPECTED_BUILDINGS = 8
EXPECTED_DATES = 155
EXPECTED_OUTCOMES = {
    "COLLISIONMORTALITY_X": {"sum": 152, "positive_rows": 142, "zero_rows": 8693},
    "COLLISIONS_X": {"sum": 199, "positive_rows": 186, "zero_rows": 8649},
}
EXPECTED_METHOD_COUNTS = {"1": 4845, "2": 3990}
EXPECTED_SEASON_COUNTS = {"fall": 1881, "winter": 3192, "spring": 1881, "summer": 1881}

FEATURE_ALIASES = {
    "facade_area_m2": ("FACADE_AREA", "FacArea"),
    "glass_area_m2": ("AREA_GLASS", "AreaGlass"),
    "facade_porous_cover_percent": ("PERC_VEG_AND_POROUS_SURFACE_FACADE", "VegPer"),
    "facade_tree_cover_percent": ("TREECOVER_FACADE_PERCENT", "TreeCov"),
    "stories_reflecting_canopy": ("STORIES_REFLECT_CANOPY", "StorReflVeg"),
    "building_vegetation_proportion_0_1": ("VEGE_PERC",),
    "building_storeys": ("STOREYS",),
    "facade_direction": ("DIRECTION",),
    "facade_orientation_angle_degrees": ("ANGLE_FROM_LINEAR_DIR_MEAN",),
}
OUTCOME_COLUMNS = ("COLLISIONMORTALITY_X", "COLLISIONS_X")


def _read_csv(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = raw.decode("utf-8-sig")
    if text.lstrip().lower().startswith(("<!doctype html", "<html", "<?xml")):
        raise ValueError("Appendix URL returned an HTML/XML document, not a CSV")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = list(reader.fieldnames or [])
    if not headers:
        raise ValueError("Appendix CSV has no header row")
    if len(headers) != len(set(headers)):
        raise ValueError(f"Appendix CSV has duplicate headers: {headers}")
    rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("Appendix CSV contains no data rows")
    return headers, rows


def _numeric(values: list[str]) -> tuple[list[float], int, list[str]]:
    parsed, missing, invalid = [], 0, []
    for value in values:
        text = (value or "").strip()
        if not text or text.upper() in {"NA", "N/A", "NULL", "UNKNOWN"}:
            missing += 1
            continue
        try:
            number = float(text)
        except ValueError:
            invalid.append(text)
            continue
        if not math.isfinite(number):
            invalid.append(text)
            continue
        parsed.append(number)
    return parsed, missing, invalid


def _feature_column(headers: list[str], aliases: tuple[str, ...]) -> str | None:
    by_lower = {name.strip().lower(): name for name in headers}
    for alias in aliases:
        if alias.strip().lower() in by_lower:
            return by_lower[alias.strip().lower()]
    return None


def inspect_appendix(raw: bytes, source_url: str = SOURCE_URL, strict: bool = False) -> dict:
    headers, rows = _read_csv(raw)
    sha256 = hashlib.sha256(raw).hexdigest()
    columns = {
        feature: _feature_column(headers, aliases)
        for feature, aliases in FEATURE_ALIASES.items()
    }
    required = {
        "SURVEY_DATE", "SEASON", "BUILDING_X", "FACADE", "METHOD",
        "COLLISIONMORTALITY_X", "COLLISIONS_X",
    }
    missing_required = sorted(required - set(headers))
    if missing_required:
        raise ValueError(f"Appendix is missing required survey fields: {missing_required}")

    facade_rows: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    survey_key_counts: Counter[tuple[str, str, str]] = Counter()
    date_counts: Counter[str] = Counter()
    building_values = set()
    season_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    for row in rows:
        building = (row.get("BUILDING_X") or "").strip()
        facade = (row.get("FACADE") or "").strip()
        survey_date = (row.get("SURVEY_DATE") or "").strip()
        if not building or not facade or not survey_date:
            raise ValueError("Appendix contains an empty building/facade/date key")
        facade_rows[(building, facade)].append(row)
        survey_key_counts[(building, facade, survey_date)] += 1
        date_counts[survey_date] += 1
        building_values.add(building)
        season_counts[(row.get("SEASON") or "").strip().lower()] += 1
        method_counts[(row.get("METHOD") or "").strip()] += 1

    duplicate_survey_keys = [
        {"building": key[0], "facade": key[1], "date": key[2], "rows": count}
        for key, count in sorted(survey_key_counts.items()) if count > 1
    ]
    rows_per_facade = Counter(len(value) for value in facade_rows.values())
    facades_per_date = Counter(date_counts.values())
    expected_panel_rows = len(facade_rows) * len(date_counts)

    outcomes = {}
    for column in OUTCOME_COLUMNS:
        values, missing, invalid = _numeric([row.get(column, "") for row in rows])
        outcomes[column] = {
            "sum": sum(values),
            "positive_rows": sum(value > 0 for value in values),
            "zero_rows": sum(value == 0 for value in values),
            "missing": missing,
            "invalid": len(invalid),
            "invalid_examples": invalid[:5],
            "max": max(values) if values else None,
        }

    feature_summary = {}
    for feature, column in columns.items():
        if column is None:
            feature_summary[feature] = {"column": None, "present": False}
            continue
        values, missing, invalid = _numeric([row.get(column, "") for row in rows])
        per_facade_values = {
            key: {((r.get(column) or "").strip()) for r in group}
            for key, group in facade_rows.items()
        }
        nonconstant_facades = [
            {"building": key[0], "facade": key[1], "distinct_values": len(vals)}
            for key, vals in per_facade_values.items() if len(vals) > 1
        ]
        summary = {
            "column": column,
            "present": True,
            "nonmissing": len(values),
            "missing": missing,
            "invalid_numeric": len(invalid),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": sum(values) / len(values) if values else None,
            "constant_within_facade": len(nonconstant_facades) == 0,
            "nonconstant_facade_count": len(nonconstant_facades),
            "nonconstant_facade_examples": nonconstant_facades[:5],
        }
        if feature in {"facade_porous_cover_percent", "facade_tree_cover_percent"}:
            summary["outside_0_100"] = sum(value < 0 or value > 100 for value in values)
        elif feature == "building_vegetation_proportion_0_1":
            summary["outside_0_1"] = sum(value < 0 or value > 1 for value in values)
        elif feature in {"facade_area_m2", "glass_area_m2", "stories_reflecting_canopy", "building_storeys"}:
            summary["negative_values"] = sum(value < 0 for value in values)
        if feature == "glass_area_m2" and columns["facade_area_m2"]:
            facade_col = columns["facade_area_m2"]
            violations = []
            for key, group in facade_rows.items():
                try:
                    glass = float(group[0][column])
                    facade_area = float(group[0][facade_col])
                except (TypeError, ValueError):
                    continue
                if glass > facade_area + 1e-8:
                    violations.append({"building": key[0], "facade": key[1], "glass_area_m2": glass, "facade_area_m2": facade_area})
            summary["glass_area_exceeds_facade_area"] = len(violations)
            summary["glass_area_exceeds_facade_area_examples"] = violations[:5]
        feature_summary[feature] = summary

    building_vegetation_column = columns["building_vegetation_proportion_0_1"]
    building_vegetation = {}
    if building_vegetation_column:
        for building in sorted(building_values):
            values = {
                (row.get(building_vegetation_column) or "").strip()
                for row in rows if row["BUILDING_X"].strip() == building
            }
            building_vegetation[building] = sorted(values)

    report = {
        "source": {
            "url": source_url,
            "paper_doi": PAPER_DOI,
            "citation": "Zulian et al. 2023, Avian Conservation and Ecology 18(2):15",
            "license": "CC BY 4.0 article; attribute source and identify changes",
            "bytes": len(raw),
            "sha256": sha256,
            "expected_sha256": EXPECTED_SHA256,
            "sha256_matches_pin": sha256 == EXPECTED_SHA256,
        },
        "grain": "one row per facade x survey date; repeated measures are already in this file",
        "row_count": len(rows),
        "column_count": len(headers),
        "columns": headers,
        "panel": {
            "buildings": len(building_values),
            "facades": len(facade_rows),
            "survey_dates": len(date_counts),
            "facade_date_rows": len(survey_key_counts),
            "duplicate_facade_date_keys": len(duplicate_survey_keys),
            "duplicate_examples": duplicate_survey_keys[:10],
            "expected_complete_grid_rows": expected_panel_rows,
            "complete_facade_date_grid": len(rows) == expected_panel_rows and not duplicate_survey_keys,
            "rows_per_facade_distribution": {str(k): v for k, v in sorted(Counter(len(v) for v in facade_rows.values()).items())},
            "facades_per_date_distribution": {str(k): v for k, v in sorted(facades_per_date.items())},
        },
        "outcomes": outcomes,
        "method_counts": dict(sorted(method_counts.items())),
        "season_counts": dict(sorted(season_counts.items())),
        "season_year_missing_rows": sum(not (row.get("SEASON_YEAR") or "").strip() for row in rows),
        "feature_columns": columns,
        "feature_summary": feature_summary,
        "building_level_vegetation_proportion": building_vegetation,
        "preview_rows": rows[:5],
        "interpretation_limits": [
            "COLLISIONMORTALITY_X is the primary carcass-mortality count; the paper's binomial response is 1 when this count is positive and 0 otherwise.",
            "COLLISIONS_X is a separate broader collision field; do not substitute it for the carcass-presence response without a documented definition.",
            "METHOD is the survey interval code (1=24 hours, 2=48 hours); the model offset is log(hours since the previous survey), not the raw category code.",
            "VEGE_PERC is a building-level proportion; PERC_VEG_AND_POROUS_SURFACE_FACADE is the façade-specific 50-m buffer variable used as VegPer.",
            "TREECOVER_FACADE_PERCENT and STORIES_REFLECT_CANOPY are façade-level variables; they are not interchangeable with building-level VEGE_PERC.",
            "The data are UBC temperate-campus observations, not BNBU measurements.",
            "The response is detected carcass presence, not true bird approach probability or detection-corrected mortality.",
            "The De Groot raw collision CSV is a separate data version: do not row-join the two files without a date/outcome reconciliation. Use this appendix as the primary model panel.",
        ],
    }

    if strict:
        if sha256 != EXPECTED_SHA256:
            raise ValueError(f"Appendix SHA-256 mismatch: expected {EXPECTED_SHA256}, got {sha256}")
        if len(rows) != EXPECTED_ROWS or len(headers) != EXPECTED_COLUMNS:
            raise ValueError(f"Appendix dimensions changed: rows={len(rows)}, columns={len(headers)}")
        if report["panel"]["buildings"] != EXPECTED_BUILDINGS or report["panel"]["facades"] != EXPECTED_FACADES:
            raise ValueError(f"Appendix building/facade count changed: {report['panel']}")
        if report["panel"]["survey_dates"] != EXPECTED_DATES or not report["panel"]["complete_facade_date_grid"]:
            raise ValueError(f"Appendix facade-date panel is incomplete: {report['panel']}")
        if report["panel"]["rows_per_facade_distribution"] != {"155": 57}:
            raise ValueError("Appendix rows-per-facade distribution changed")
        if report["panel"]["facades_per_date_distribution"] != {"57": 155}:
            raise ValueError("Appendix facades-per-date distribution changed")
        for column, expected in EXPECTED_OUTCOMES.items():
            observed = report["outcomes"][column]
            for key, value in expected.items():
                if observed[key] != value:
                    raise ValueError(f"{column} {key} changed: {observed[key]} != {value}")
        if dict(method_counts) != EXPECTED_METHOD_COUNTS:
            raise ValueError(f"Appendix METHOD counts changed: {dict(method_counts)}")
        if dict(season_counts) != EXPECTED_SEASON_COUNTS:
            raise ValueError(f"Appendix SEASON counts changed: {dict(season_counts)}")
        required_features = (
            "facade_area_m2", "glass_area_m2", "facade_porous_cover_percent",
            "facade_tree_cover_percent", "stories_reflecting_canopy",
        )
        missing_features = [name for name in required_features if not columns[name]]
        if missing_features:
            raise ValueError(f"Appendix is missing required façade predictors: {missing_features}")
        for name in required_features:
            if not feature_summary[name]["constant_within_facade"]:
                raise ValueError(f"Feature {name} is not constant within facade")
        if feature_summary["glass_area_m2"]["glass_area_exceeds_facade_area"] != 0:
            raise ValueError("Glass area exceeds facade area")
        if feature_summary["facade_porous_cover_percent"]["outside_0_100"] != 0:
            raise ValueError("Facade porous-cover percentage is outside [0,100]")
        if feature_summary["facade_tree_cover_percent"]["outside_0_100"] != 0:
            raise ValueError("Facade tree-cover percentage is outside [0,100]")
        if feature_summary["building_vegetation_proportion_0_1"]["outside_0_1"] != 0:
            raise ValueError("Building vegetation proportion is outside [0,1]")

    return report


def download_appendix(timeout: int = 45) -> bytes:
    request = Request(SOURCE_URL, headers={"User-Agent": "BNBU-BirdGlass-Research/1.0"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    if not raw:
        raise ValueError("Appendix download returned an empty file")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--csv-out", type=Path, default=Path("data/derived/ubc/zulian_appendix1.csv"))
    parser.add_argument("--report-out", type=Path, default=Path("data/derived/ubc/zulian_appendix_inspection.json"))
    args = parser.parse_args()
    if args.download == (args.input is not None):
        parser.error("Choose exactly one of --download or --input")
    if args.download:
        raw = download_appendix()
        args.csv_out.parent.mkdir(parents=True, exist_ok=True)
        args.csv_out.write_bytes(raw)
        source = SOURCE_URL
    else:
        raw = args.input.read_bytes()
        source = str(args.input)
    report = inspect_appendix(raw, source, strict=args.strict)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "row_count": report["row_count"],
        "column_count": report["column_count"],
        "sha256": report["source"]["sha256"],
        "panel": report["panel"],
        "outcomes": report["outcomes"],
        "method_counts": report["method_counts"],
        "season_counts": report["season_counts"],
        "feature_columns": report["feature_columns"],
        "feature_summary": report["feature_summary"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
