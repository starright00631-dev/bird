#!/usr/bin/env python3
"""Download and schema-audit Zulian et al. (2023) Appendix 1.

This is an inspection step only. It does not infer a join key, recode values,
or fit a model. The downloaded appendix is kept in an ignored CI data folder.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://ace-eco.org/vol18/iss2/art15/appendix1.csv"
PAPER_DOI = "10.5751/ACE-02482-180215"


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _read_csv(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = raw.decode("utf-8-sig")
    if text.lstrip().lower().startswith(("<!doctype html", "<html", "<?xml")):
        raise ValueError("Appendix URL returned an HTML/XML document, not a CSV")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = list(reader.fieldnames or [])
    if not headers:
        raise ValueError("Appendix CSV has no header row")
    normalized = [normalize(name) for name in headers]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"Appendix CSV has duplicate/ambiguous normalized headers: {headers}")
    rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("Appendix CSV contains no data rows")
    return headers, rows


def _find_alias(headers: list[str], aliases: tuple[str, ...]) -> str | None:
    by_normalized = {normalize(name): name for name in headers}
    for alias in aliases:
        if normalize(alias) in by_normalized:
            return by_normalized[normalize(alias)]
    return None


def inspect_appendix(raw: bytes, source_url: str = SOURCE_URL) -> dict:
    headers, rows = _read_csv(raw)
    normalized_to_original = {normalize(name): name for name in headers}

    building_col = _find_alias(headers, (
        "Building", "Building ID", "BUILDING_X", "BUILDING.X", "Build",
    ))
    facade_col = _find_alias(headers, (
        "Facade", "Facade ID", "FACADE_ID", "Building_Facade", "Build:Fac",
    ))
    feature_aliases = {
        "facade_area": ("FacArea", "Facade Area", "FACADE_AREA"),
        "glass_area": ("AreaGlass", "Glass Area", "AREA_GLASS"),
        "porous_vegetation_percent": ("VegPer", "VegPerc", "VEG_PER", "VEGE_PERC"),
        "tree_cover_percent": ("TreeCov", "Tree Cover", "TREE_COV"),
        "stories_reflecting_vegetation": ("StorReflVeg", "Stories Reflecting Vegetation", "STOR_REFL_VEG"),
    }
    features = {
        key: _find_alias(headers, aliases)
        for key, aliases in feature_aliases.items()
    }

    def nonempty(value: str | None) -> bool:
        return bool((value or "").strip())

    key_audit = {
        "building_column": building_col,
        "facade_column": facade_col,
        "building_missing": sum(not nonempty(row.get(building_col)) for row in rows) if building_col else None,
        "facade_missing": sum(not nonempty(row.get(facade_col)) for row in rows) if facade_col else None,
        "composite_key_unique": None,
        "unique_composite_keys": None,
        "duplicate_composite_key_count": None,
        "duplicate_composite_key_examples": [],
    }
    if building_col and facade_col:
        keys = [
            ((row.get(building_col) or "").strip(), (row.get(facade_col) or "").strip())
            for row in rows
        ]
        counts: dict[tuple[str, str], int] = {}
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
        duplicates = [
            {"building": key[0], "facade": key[1], "rows": count}
            for key, count in sorted(counts.items()) if count > 1
        ]
        key_audit.update({
            "composite_key_unique": len(counts) == len(rows) and all(a and b for a, b in keys),
            "unique_composite_keys": len(counts),
            "duplicate_composite_key_count": len(duplicates),
            "duplicate_composite_key_examples": duplicates[:10],
        })

    feature_summary = {}
    for feature, column in features.items():
        if column is None:
            feature_summary[feature] = {"column": None, "present": False}
            continue
        parsed = []
        invalid = []
        missing = 0
        for row_index, row in enumerate(rows, start=2):
            value = (row.get(column) or "").strip()
            if not value or value.upper() in {"NA", "N/A", "NULL", "UNKNOWN"}:
                missing += 1
                continue
            try:
                number = float(value)
            except ValueError:
                invalid.append({"row": row_index, "value": value})
                continue
            if not (number == number and abs(number) != float("inf")):
                invalid.append({"row": row_index, "value": value})
                continue
            parsed.append(number)
        summary = {
            "column": column,
            "present": True,
            "nonmissing": len(parsed),
            "missing": missing,
            "invalid_numeric": len(invalid),
            "min": min(parsed) if parsed else None,
            "max": max(parsed) if parsed else None,
            "mean": sum(parsed) / len(parsed) if parsed else None,
            "invalid_examples": invalid[:5],
        }
        if feature in {"porous_vegetation_percent", "tree_cover_percent"}:
            summary["outside_0_100"] = sum(value < 0 or value > 100 for value in parsed)
        elif feature in {"facade_area", "glass_area", "stories_reflecting_vegetation"}:
            summary["negative_values"] = sum(value < 0 for value in parsed)
        if feature == "glass_area" and features["facade_area"]:
            facade_area_col = features["facade_area"]
            violations = []
            for row_index, row in enumerate(rows, start=2):
                try:
                    glass = float(row[column])
                    facade = float(row[facade_area_col])
                except (TypeError, ValueError):
                    continue
                if glass > facade + 1e-8:
                    violations.append({"row": row_index, "glass_area": glass, "facade_area": facade})
            summary["glass_area_exceeds_facade_area"] = len(violations)
            summary["glass_area_exceeds_facade_area_examples"] = violations[:5]
        feature_summary[feature] = summary

    return {
        "source": {
            "url": source_url,
            "paper_doi": PAPER_DOI,
            "citation": "Zulian et al. 2023, Avian Conservation and Ecology 18(2):15",
            "license": "CC BY 4.0 article; attribute source and identify changes",
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "row_count": len(rows),
        "column_count": len(headers),
        "columns": headers,
        "key_audit": key_audit,
        "feature_columns": features,
        "feature_summary": feature_summary,
        "preview_rows": rows[:8],
        "interpretation_limits": [
            "This appendix is a façade-level covariate table, not the 8,835-row repeated collision-survey outcome table.",
            "A composite building/facade key is only a candidate join key until its labels are matched to the observed collision source.",
            "These variables describe the UBC temperate campus; they are not BNBU measurements.",
            "The source paper's response is detected carcass presence per survey, not true bird approach probability or detection-corrected mortality.",
        ],
    }


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
    report = inspect_appendix(raw, source)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "row_count": report["row_count"],
        "column_count": report["column_count"],
        "sha256": report["source"]["sha256"],
        "columns": report["columns"],
        "key_audit": report["key_audit"],
        "feature_columns": report["feature_columns"],
        "feature_summary": report["feature_summary"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
