#!/usr/bin/env python3
"""Checksum-pinned audit for UBC bird-window collision data.

De Groot et al. Dryad files and Zulian et al. Appendix 1 are distinct source
products. This script preserves explicit survey zeroes, repeated search
histories, and censored persistence intervals. It is not a collision model.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import urllib.request
from pathlib import Path

ZENODO_RECORD = 6373683
DRYAD_DOI = "10.5061/dryad.hqbzkh1g6"
ACE_APPENDIX_URL = "https://ace-eco.org/vol18/iss2/art15/appendix1.csv"
FILES = {
    "Carcass.Persistence.csv": ("61dd1e109bb22925cd91b9b697ae4c9c", None),
    "Observed.Collision.Counts.csv": ("9e0c551f430e75e337a6b6da750a0d00", None),
    "READ.ME.xlsx": ("299d4a431186ada9a47950b5824a2a93", None),
    "Search.Efficiency.csv": ("f9e7a8816ef52eb9d3523f0f14b40d6b", 1766),
    "Search.Schedule.csv": ("729cde12568d04a8b102726b8112533b", None),
    "UBC.point.counts.csv": ("760e513ad29905159dbb886ccf532208", None),
}
EXPECTED = {
    "survey_rows": 8835, "facades": 57, "buildings": 8,
    "survey_days": 155, "positive_facade_surveys": 142, "species": 23,
}
ALIASES = {
    "building": ("building", "build", "buildingname", "buildingid", "buildid"),
    "facade": ("facade", "fac", "facadeid", "facid", "facadename"),
    "date": ("date", "surveydate", "sampledate", "dateofsurvey", "surveyday"),
    "season": ("season", "seasonname", "seasonby5", "period"),
    "response": ("collision", "collisions", "collisioncount", "birdcollision",
                 "evidence", "presence", "collisionpresent"),
    "species": ("species", "scientificname", "taxon", "birdspecies"),
}


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def missing(value):
    return value is None or str(value).strip().casefold() in {
        "", "na", "n/a", "n.a.", "nan", "null", "unknown", "-", "."
    }


def number(value):
    if missing(value):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"No CSV header: {path}")
        headers = [str(x).strip() for x in reader.fieldnames]
        if len(headers) != len(set(headers)):
            raise ValueError(f"Duplicate CSV headers: {path}")
        rows = [
            {str(k).strip(): (v or "").strip()
             for k, v in row.items() if k is not None}
            for row in reader
        ]
    return headers, rows


def find_column(headers, role):
    by_name = {normalize(h): h for h in headers}
    return next((by_name[a] for a in ALIASES[role] if a in by_name), None)


def audit_search_efficiency(path):
    headers, rows = read_csv(path)
    by_name = {normalize(h): h for h in headers}
    visits = [by_name[f"s{i}"] for i in range(1, 7) if f"s{i}" in by_name]
    if not visits:
        return {"status": "schema_mapping_required", "rows": len(rows),
                "columns": headers}
    at_risk = rows
    hazards = []
    for i, col in enumerate(visits, 1):
        eligible = detections = missings = invalid = 0
        next_risk = []
        for row in at_risk:
            value = row.get(col)
            if missing(value):
                missings += 1
                continue
            if str(value).strip() not in {"0", "1", "0.0", "1.0"}:
                invalid += 1
                continue
            eligible += 1
            found = float(value) == 1.0
            detections += int(found)
            if not found:
                next_risk.append(row)
        hazards.append({
            "search_number": i, "column": col,
            "at_risk_trials_with_observed_result": eligible,
            "detections_on_this_search": detections,
            "conditional_detection_fraction": detections / eligible if eligible else None,
            "missing_while_at_risk": missings, "invalid_values": invalid,
        })
        at_risk = next_risk
    season_col = find_column(headers, "season")
    seasonal = {}
    if season_col:
        for season in sorted({r[season_col] for r in rows if not missing(r.get(season_col))}):
            group = [r for r in rows if r.get(season_col) == season]
            observed = [r for r in group if not missing(r.get(visits[0]))]
            found = sum(str(r.get(visits[0])).strip() in {"1", "1.0"} for r in observed)
            seasonal[season] = {
                "trials": len(group), "first_search_observed": len(observed),
                "first_search_detections": found,
                "first_search_fraction": found / len(observed) if observed else None,
            }
    return {
        "status": "repeated_detection_history_parsed", "rows": len(rows),
        "visit_columns": visits, "season_column": season_col,
        "first_search_by_season": seasonal,
        "conditional_detection_by_search": hazards,
        "interpretation": (
            "Descriptive trial hazards only. Detection ends the at-risk sequence; "
            "later NA values are not zero detections. Fit search efficiency and "
            "carcass persistence jointly before correcting collision counts."
        ),
    }


def audit_carcass_persistence(path):
    headers, rows = read_csv(path)
    by_name = {normalize(h): h for h in headers}
    lower = next((by_name[k] for k in
                  ("lastpresent", "lastseen", "lastpresenttime", "lastcheckpresent")
                  if k in by_name), None)
    upper = next((by_name[k] for k in
                  ("firstabsent", "firstmissing", "firstabsenttime", "firstcheckabsent")
                  if k in by_name), None)
    if not lower or not upper:
        return {"status": "schema_mapping_required", "rows": len(rows),
                "columns": headers}
    interval = right_censored = invalid = 0
    for row in rows:
        lo, hi = row.get(lower), row.get(upper)
        if missing(lo):
            invalid += 1
        elif missing(hi):
            right_censored += 1
        else:
            interval += 1
    return {
        "status": "interval_censoring_fields_detected", "rows": len(rows),
        "last_present_column": lower, "first_absent_column": upper,
        "interval_censored_trials": interval,
        "right_censored_trials": right_censored,
        "invalid_or_incomplete_trials": invalid,
        "interpretation": (
            "Removal lies between last-present and first-absent checks. A carcass "
            "still present at the final check is right-censored; do not replace "
            "check intervals with exact removal times."
        ),
    }


def audit_survey_table(path, expected=None):
    headers, rows = read_csv(path)
    columns = {role: find_column(headers, role) for role in ALIASES}
    response = columns["response"]
    positive = zero = unknown = 0
    vals = []
    positive_sum = 0.0
    if response:
        for row in rows:
            value = row.get(response)
            if not missing(value):
                vals.append(value)
            n = number(value)
            if missing(value):
                unknown += 1
            elif n is not None:
                if n > 0:
                    positive += 1
                    positive_sum += n
                else:
                    zero += 1
            elif str(value).strip().casefold() in {
                "yes", "true", "present", "positive", "collision"
            }:
                positive += 1
                positive_sum += 1
            elif str(value).strip().casefold() in {
                "no", "false", "absent", "negative", "none"
            }:
                zero += 1
            else:
                unknown += 1
    nums = [number(v) for v in vals]
    nums = [v for v in nums if v is not None]
    binary = bool(nums) and all(v in {0.0, 1.0} for v in nums)
    unique = {}
    for role in ("building", "facade", "date", "season", "species"):
        col = columns[role]
        unique[role] = (
            len({r.get(col, "") for r in rows if col and not missing(r.get(col))})
            if col else None
        )
    observed = {
        "survey_rows": len(rows), "facades": unique["facade"],
        "buildings": unique["building"], "survey_days": unique["date"],
        "positive_facade_surveys": positive if response else None,
        "species": unique["species"],
    }
    checks = {
        k: {"expected": v, "observed": observed.get(k),
            "match": observed.get(k) == v}
        for k, v in (expected or EXPECTED).items()
    }
    return {
        "filename": Path(path).name, "rows": len(rows), "columns": headers,
        "detected_columns": columns, "unique_counts": unique,
        "response_column": response,
        "response_type": ("binary_presence" if binary else
                          ("numeric_count" if nums else "categorical_or_unmapped")),
        "explicit_zero_rows": zero, "positive_rows": positive,
        "unknown_response_rows": unknown,
        "sum_of_positive_numeric_responses": positive_sum if response and nums else None,
        "published_collision_event_count_reference": 152,
        "published_benchmark_checks": checks,
        "zero_handling": "Only explicit completed-survey zeroes are non-events; absent rows are not synthesized as zeroes.",
        "warning": (
            "The paper reports 142 positive facade-surveys and 152 individual "
            "collision events. A binary 0/1 response cannot be summed to recover 152."
        ),
    }


def download_file(filename, destination):
    if filename not in FILES:
        raise ValueError(f"Unpinned source file: {filename}")
    expected_md5, expected_bytes = FILES[filename]
    url = f"https://zenodo.org/records/{ZENODO_RECORD}/files/{filename}?download=1"
    request = urllib.request.Request(
        url, headers={"User-Agent": "BNBU-BirdGlass-Research/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    actual = hashlib.md5(payload).hexdigest()
    if actual != expected_md5:
        raise ValueError(f"MD5 mismatch for {filename}: expected {expected_md5}, got {actual}")
    if expected_bytes is not None and len(payload) != expected_bytes:
        raise ValueError(f"Size mismatch for {filename}: expected {expected_bytes}, got {len(payload)}")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {"filename": filename, "bytes": len(payload), "md5": actual, "url": url}


def audit_dataset(data_dir, appendix1=None):
    data_dir = Path(data_dir)
    present = sorted(name for name in FILES if (data_dir / name).exists())
    summaries = {}
    for name in present:
        if name.endswith(".csv"):
            headers, rows = read_csv(data_dir / name)
            summaries[name] = {
                "rows": len(rows), "columns": headers,
                "missing_by_column": {
                    h: sum(missing(r.get(h)) for r in rows) for h in headers
                },
            }
    result = {
        "source": {
            "dryad_doi": DRYAD_DOI,
            "dryad_landing_page": f"https://datadryad.org/dataset/doi:{DRYAD_DOI}",
            "zenodo_record": ZENODO_RECORD,
            "zenodo_landing_page": f"https://zenodo.org/records/{ZENODO_RECORD}",
            "ace_eco_facade_appendix": ACE_APPENDIX_URL,
        },
        "files_present": present,
        "files_missing": sorted(set(FILES) - set(present)),
        "csv_summaries": summaries,
        "scientific_constraints": [
            "De Groot Dryad files and Zulian 2023 Appendix 1 are distinct products; do not join without verified keys and compatible row grain.",
            "Search-efficiency and persistence trials model the observation process, not collision outcomes.",
            "Only explicit completed-survey zeroes are non-events; missing or unvisited façades are not zeroes.",
            "UBC is a temperate Pacific transfer benchmark, not Guangdong/BNBU calibration truth.",
        ],
    }
    search = data_dir / "Search.Efficiency.csv"
    if search.exists():
        result["search_efficiency"] = audit_search_efficiency(search)
    persistence = data_dir / "Carcass.Persistence.csv"
    if persistence.exists():
        result["carcass_persistence"] = audit_carcass_persistence(persistence)
    if appendix1 is not None:
        result["facade_survey_appendix"] = audit_survey_table(appendix1)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--appendix1", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    downloaded = (
        [download_file(name, args.data_dir / name) for name in FILES]
        if args.fetch else []
    )
    report = audit_dataset(args.data_dir, args.appendix1)
    report["downloaded_files_this_run"] = downloaded
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
