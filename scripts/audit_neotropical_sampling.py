"""Audit the Neotropical bird-window collision event dataset.

Each row is a curated reported collision event, not a surveyed non-event or
a complete set of bird approaches. The audit is descriptive only.

Pinned source:
  Piratelli et al. (2025), Ecology 106(6):e70126
  https://doi.org/10.1002/ecy.70126
  https://doi.org/10.5281/zenodo.15271126

Usage:
  python scripts/audit_neotropical_sampling.py BWC_Neotropical_region.csv
  python scripts/audit_neotropical_sampling.py --fetch-pinned --out results/neotropical_audit.json
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
    "General.ID", "Country", "Latitude", "Longitude",
    "Data.collection.method", "Pane.type", "Deterrent", "Survivorship",
    "Month", "Date.accuracy", "Age", "Sex", "Species",
)


def _unknown(value: str | None) -> bool:
    return value is None or value.strip().casefold() in {"", "unknown", "n/a", "na"}


def _geo_key(row: dict[str, str]) -> str:
    """Country plus published coordinates: a coarse proxy, not a building ID."""
    lat, lon = row["Latitude"], row["Longitude"]
    if _unknown(lat) or _unknown(lon):
        return "unlocated|" + row["General.ID"]
    return "|".join((row["Country"], lat.strip(), lon.strip()))


def _row_is_train(row: dict[str, str]) -> bool:
    """Stable 80/20 row-hash diagnostic; not a recommended model split."""
    key = int(row["General.ID"])
    return ((key * 2654435761) & 0xFFFFFFFF) / 4294967296 < 0.8


def _counts(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counter = Counter(r.get(field, "") for r in rows)
    return dict(counter.most_common())


def audit_rows(rows: list[dict[str, str]]) -> dict:
    if not rows:
        raise ValueError("Empty dataset")
    if any(set(REQUIRED) - set(row) for row in rows):
        raise ValueError("Required columns missing")
    ids = [row["General.ID"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate General.ID rows")

    countries = Counter(row["Country"] for row in rows)
    methods = Counter(row["Data.collection.method"] for row in rows)
    species = Counter(row["Species"] for row in rows if not _unknown(row["Species"]))
    method_by_country = defaultdict(Counter)
    survival_by_method = defaultdict(Counter)
    pane_by_method = defaultdict(Counter)
    month_by_method = defaultdict(Counter)
    coordinate_keys = Counter()
    for row in rows:
        method = row["Data.collection.method"]
        method_by_country[row["Country"]][method] += 1
        survival_by_method[method][row["Survivorship"]] += 1
        pane_by_method[method][row["Pane.type"]] += 1
        month_by_method[method][row["Month"]] += 1
        coordinate_keys[_geo_key(row)] += 1

    train_keys = {_geo_key(row) for row in rows if _row_is_train(row)}
    heldout = [row for row in rows if not _row_is_train(row)]
    shared_coordinate_proxy = sum(_geo_key(row) in train_keys for row in heldout)

    country_folds = []
    for country in sorted(countries):
        test_n = countries[country]
        country_folds.append({
            "held_out_country": country,
            "test_records": test_n,
            "train_records": len(rows) - test_n,
            "train_countries": len(countries) - 1,
            "country_overlap": False,
            "purpose": "descriptive transfer of reported-event composition only",
        })

    year_values = []
    for row in rows:
        if not _unknown(row.get("Year")):
            try:
                year_values.append(int(row["Year"]))
            except ValueError:
                pass

    unknown_counts = {
        field: sum(_unknown(row.get(field)) for row in rows)
        for field in REQUIRED
    }

    return {
        "source_url": SOURCE_URL,
        "source_git_blob_sha": SOURCE_GIT_BLOB,
        "unit": "curated reported bird-window collision event",
        "records": len(rows),
        "unique_species": len(species),
        "countries": dict(countries.most_common()),
        "collection_methods": dict(methods.most_common()),
        "pane_types": _counts(rows, "Pane.type"),
        "deterrents": _counts(rows, "Deterrent"),
        "reported_survivorship": _counts(rows, "Survivorship"),
        "date_accuracy": _counts(rows, "Date.accuracy"),
        "months": _counts(rows, "Month"),
        "top_species": dict(species.most_common(25)),
        "year_range": [min(year_values), max(year_values)] if year_values else None,
        "unknown_counts": unknown_counts,
        "collection_method_by_country": {
            country: dict(counter.most_common())
            for country, counter in sorted(method_by_country.items())
        },
        "reported_survival_by_collection_method": {
            method: dict(counter.most_common())
            for method, counter in sorted(survival_by_method.items())
        },
        "pane_type_by_collection_method": {
            method: dict(counter.most_common())
            for method, counter in sorted(pane_by_method.items())
        },
        "month_by_collection_method": {
            method: dict(counter.most_common())
            for method, counter in sorted(month_by_method.items())
        },
        "coordinate_proxy": {
            "unique_country_coordinate_keys": len(coordinate_keys),
            "records_in_repeated_keys": sum(
                count for count in coordinate_keys.values() if count >= 2
            ),
            "max_records_at_one_key": max(coordinate_keys.values()),
            "interpretation": (
                "Repeated coordinates may be rounded or reused; they are not "
                "proof of one building, observer or independent survey."
            ),
        },
        "row_split_diagnostic": {
            "method": "80/20 stable General.ID hash; not grouped",
            "heldout_rows": len(heldout),
            "heldout_rows_sharing_country_coordinate_proxy": shared_coordinate_proxy,
            "share": (
                shared_coordinate_proxy / len(heldout) if heldout else None
            ),
            "warning": (
                "This diagnostic is not a leakage estimate at building level. "
                "Coordinate keys are only coarse proxies."
            ),
        },
        "country_holdout_folds": country_folds,
        "estimable_target": (
            "composition of reported collision events conditional on "
            "reporting, collection method and source selection"
        ),
        "not_estimable": [
            "P(collision | bird approach)",
            "incidence per building, pane, survey hour or approach",
            "causal effect of pane type or deterrent",
            "population-wide mortality or species susceptibility",
            "local Guangdong species abundance or seasonal approach flow",
        ],
        "recommended_use": [
            "species/event taxonomy and source-method audit",
            "descriptive event composition",
            "hypothesis generation for variables to measure locally",
        ],
        "prohibited_use": [
            "binary collision classifier trained as if every row were a positive "
            "sample from a complete risk set",
            "causal treatment-effect estimation",
            "BNBU collision probability calibration",
        ],
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
    """Download the public CSV and reject unreviewed source mutations."""
    with urlopen(RAW_URL, timeout=45) as response:
        data = response.read()
    blob_hash = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    if blob_hash != SOURCE_GIT_BLOB:
        raise ValueError(
            f"Dataset changed: expected {SOURCE_GIT_BLOB}, got {blob_hash}"
        )
    return data.decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, nargs="?", help="Local source CSV")
    parser.add_argument("--fetch-pinned", action="store_true")
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
