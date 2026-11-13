"""Audit sampling bias in the public Neotropical bird-window-collision event table.

Data: Piratelli et al. (2025), BWC_Neotropical_region.csv.
Each row is a reported collision event, NOT a surveyed non-event or a bird approach.
No code here estimates incidence or P(collision | approach).

Usage:
  python scripts/audit_neotropical_sampling.py BWC_Neotropical_region.csv
  python scripts/audit_neotropical_sampling.py --fetch-pinned --out results/audit.json

When fetching, the Git blob SHA is checked to reject silent dataset mutations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen

SOURCE_URL = "https://github.com/ajpiratelli/Data-Paper-BWC/blob/main/BWC_Neotropical_region.csv"
RAW_URL = "https://raw.githubusercontent.com/ajpiratelli/Data-Paper-BWC/main/BWC_Neotropical_region.csv"
SOURCE_GIT_BLOB = "4f0205d8158e88f19f95a022bacaa06805ca31b7"
REQUIRED = (
    "General.ID", "Country", "Latitude", "Longitude", "Data.collection.method",
    "Pane.type", "Deterrent", "Survivorship", "Month", "Date.accuracy",
    "Age", "Sex", "Species",
)


def _unknown(value: str | None) -> bool:
    return value is None or value.strip().casefold() in {"", "unknown", "n/a", "na"}


def _geo_key(row: dict[str, str]) -> str:
    """Country + published coordinates: a coarse cluster, NOT a building ID."""
    lat, lon = row["Latitude"], row["Longitude"]
    if _unknown(lat) or _unknown(lon):
        return "unlocated|" + row["General.ID"]
    return "|".join((row["Country"], lat.strip(), lon.strip()))


def _row_is_train(row: dict[str, str]) -> bool:
    """Stable 80/20 row-hash demonstration, not a fitted model."""
    key = int(row["General.ID"])
    return ((key * 2654435761) & 0xFFFFFFFF) / 4294967296 < 0.8


def audit_rows(rows: list[dict[str, str]]) -> dict:
    if not rows:
        raise ValueError("Empty dataset")
    if any(set(REQUIRED) - set(r) for r in rows):
        raise ValueError("Required columns missing")
    ids = [r["General.ID"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate General.ID rows; split cannot be interpreted")

    country = Counter(r["Country"] for r in rows)
    methods = Counter(r["Data.collection.method"] for r in rows)
    method_by_country = defaultdict(Counter)
    survival = defaultdict(Counter)
    panes = defaultdict(Counter)
    coords = Counter()
    month_by_method = defaultdict(Counter)
    for row in rows:
        method = row["Data.collection.method"]
        method_by_country[row["Country"]][method] += 1
        survival[method][row["Survivorship"]] += 1
        panes[method][row["Pane.type"]] += 1
        coords[_geo_key(row)] += 1
        month_by_method[method][row["Month"]] += 1

    train_keys = {_geo_key(r) for r in rows if _row_is_train(r)}
    heldout = [r for r in rows if not _row_is_train(r)]
    shared = sum(_geo_key(r) in train_keys for r in heldout)
    unknown_counts = {k: sum(_unknown(r.get(k)) for r in rows) for k in REQUIRED}

    return {
        "reference_url": SOURCE_URL,
        "source_git_blob_sha": SOURCE_GIT_BLOB,
        "unit": "curated reported bird-window collision event",
        "estimable_target": "composition of reported events, conditional on reporting and source selection",
        "not_estimable": [
            "P(collision | bird approach)",
            "incidence per building, pane, or survey effort",
            "causal effect of deterrents, pane type, or collection method",
            "population-wide survivorship or species susceptibility",
        ],
        "records": len(rows),
        "countries": dict(country.most_common()),
        "methods": dict(methods.most_common()),
        "unknown_counts": unknown_counts,
        "reported_survival_by_collection_method": {k: dict(v) for k, v in sorted(survival.items())},
        "pane_by_collection_method": {k: dict(v) for k, v in sorted(panes.items())},
        "collection_method_by_country": {k: dict(v) for k, v in sorted(method_by_country.items())},
        "october_by_method": {
            k: {
                "october": v.get("October", 0),
                "month_known": sum(n for month, n in v.items() if not _unknown(month)),
            }
            for k, v in sorted(month_by_method.items())
        },
        "coordinate_proxy": {
            "unique_country_coordinate_keys": len(coords),
            "records_in_repeated_coordinate_keys": sum(n for n in coords.values() if n >= 2),
            "max_records_at_one_coordinate_key": max(coords.values()),
            "interpretation": "Rounded/reused lat/lon is not proof of one building or observer.",
        },
        "row_split_leakage_demo": {
            "method": "80/20 stable multiplicative ID hash; coordinates NOT grouped",
            "heldout_rows": len(heldout),
            "heldout_rows_with_same_country_coordinates_in_train": shared,
            "share": shared / len(heldout) if heldout else None,
            "interpretation": "A row split cannot test transfer to new coordinate clusters.",
        },
    }


def audit_csv_text(text: str) -> dict:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = set(REQUIRED) - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Missing CSV fields: {sorted(missing)}")
    return audit_rows(list(reader))


def audit_file(path: Path) -> dict:
    return audit_csv_text(path.read_text(encoding="utf-8-sig"))


def fetch_pinned() -> str:
    """Download the public CSV and refuse any unreviewed source changes."""
    with urlopen(RAW_URL, timeout=45) as response:
        data = response.read()
    blob_hash = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    if blob_hash != SOURCE_GIT_BLOB:
        raise ValueError(f"Dataset changed: expected {SOURCE_GIT_BLOB}, got {blob_hash}")
    return data.decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, nargs="?", help="Local copy of source CSV")
    parser.add_argument("--fetch-pinned", action="store_true", help="Fetch verified public CSV")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.fetch_pinned == (args.csv is not None):
        parser.error("Pass exactly one of a CSV path or --fetch-pinned")
    result = audit_csv_text(fetch_pinned()) if args.fetch_pinned else audit_file(args.csv)
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
