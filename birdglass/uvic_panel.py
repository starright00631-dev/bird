"""Pinned University of Victoria facade-survey ingestion and rate baseline.

This adapter rebuilds the authors' L0 collision-survey data into a panel with
one row per facade-by-seasonal-period. It keeps survey effort separate from
evidence counts and does not turn building inventory fields into pane area or
vegetation measurements.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date, datetime
from math import exp
from pathlib import Path
from typing import Mapping, Sequence
from urllib.request import Request, urlopen

SOURCE_COMMIT = "e859320c451a8fd4c6ef9e893e116e43c75a385c"
EXPECTED_VISITS_PER_FACADE_PERIOD = 21
SOURCE_FILES = {
    "fall": {
        "path": "Data/L0/collisions_data/collisionsData_Fall.csv",
        "url": (
            "https://raw.githubusercontent.com/vivizulian/"
            "BirdCollisionsUniVictoria/"
            f"{SOURCE_COMMIT}/Data/L0/collisions_data/collisionsData_Fall.csv"
        ),
        "git_blob_sha": "87b323d7c3a57a764d3b90412840120e7160c69e",
        "expected_rows": 2123,
    },
    "winter": {
        "path": "Data/L0/collisions_data/collisionsData_Winter.csv",
        "url": (
            "https://raw.githubusercontent.com/vivizulian/"
            "BirdCollisionsUniVictoria/"
            f"{SOURCE_COMMIT}/Data/L0/collisions_data/collisionsData_Winter.csv"
        ),
        "git_blob_sha": "77357637df6fa0e90ea8ed5c3cd22ab97d8efb9a",
        "expected_rows": 4214,
    },
    "buildings": {
        "path": "Data/L0/buildings_data/2024 Buildings for campus-wide estimate.csv",
        "url": (
            "https://raw.githubusercontent.com/vivizulian/"
            "BirdCollisionsUniVictoria/"
            f"{SOURCE_COMMIT}/Data/L0/buildings_data/"
            "2024%20Buildings%20for%20campus-wide%20estimate.csv"
        ),
        "git_blob_sha": "9c095b2b5c290f2ef8f8670fb688f9d05b9a3849",
        "expected_rows": 51,
    },
}

EXPECTED_PERIOD_TOTALS = {
    "Fall_2019": (1049, 117, 69),
    "Fall_2020": (1049, 108, 44),
    "LateWinter_2020": (1050, 6, 5),
    "EarlyWinter_2021": (1050, 50, 11),
    "LateWinter_2021": (1050, 27, 3),
    "LateWinter_2022": (1050, 7, 5),
}
EXPECTED_EVIDENCE_FLAG_COUNTS = {"N": 6022, "Y": 315}
EXPECTED_EVIDENCE_TYPE_COUNTS = {
    "none": 6022,
    "feather smear": 166,
    "carcass": 63,
    "feather pile": 74,
    "collision_live": 12,
}
EXPECTED_TOTALS = {
    "raw_source_rows": 6337,
    "unique_facade_day_visits": 6298,
    "facades": 50,
    "buildings": 6,
    "periods": 6,
    "collision_evidence_count": 315,
    "fatal_evidence_proxy_count": 137,
}

SURVEY_FIELDS = {
    "SURVEY_DATE",
    "BUILDING_NAME",
    "BUILDING_CODE",
    "FACADE",
    "EVIDENCE_FOUND",
    "TYPE_OF_COLLISION",
}
BUILDING_FIELDS = {"Property Name", "Number floors", "Gross Area sq m"}

PANEL_FIELDS = [
    "facade_id", "building_id", "building_name", "period_id", "season", "year",
    "period_start", "period_end", "survey_visits", "expected_survey_visits",
    "missing_expected_visits", "effort_coverage", "collision_evidence_count",
    "positive_visits", "zero_evidence_visits", "fatal_evidence_proxy_count",
    "carcass_evidence_count", "feather_pile_evidence_count",
    "feather_smear_evidence_count", "live_collision_evidence_count",
    "raw_source_rows", "extra_source_rows_within_visits",
    "building_floors_context_2024", "building_gross_area_m2_context_2024",
]


def git_blob_sha1(data: bytes) -> str:
    """Return the Git object SHA-1 for a blob, not a plain-file SHA-1."""
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def fetch_pinned_sources(timeout: int = 45) -> tuple[dict[str, str], dict[str, str]]:
    """Fetch the exact reviewed source commit and verify all Git blob hashes."""
    texts: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for name, meta in SOURCE_FILES.items():
        request = Request(meta["url"], headers={"User-Agent": "BNBU-BirdGlass-Research/1.0"})
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
        actual = git_blob_sha1(raw)
        expected = meta["git_blob_sha"]
        if actual != expected:
            raise ValueError(f"Pinned {name} source changed: expected {expected}, got {actual}")
        texts[name] = raw.decode("utf-8-sig")
        hashes[name] = actual
    return texts, hashes


def _read_dict_rows(text: str, required_fields: set[str], label: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = required_fields - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    return [dict(row) for row in reader]


def _parse_survey_date(raw: str) -> date:
    value = (raw or "").strip()
    if not value:
        raise ValueError("SURVEY_DATE cannot be empty")
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported SURVEY_DATE format: {value!r}")


def _period_for_date(day: date) -> tuple[str, str, int]:
    if day.month in (9, 10):
        season = "Fall"
    elif day.month >= 11:
        season = "EarlyWinter"
    elif day.month in (1, 2):
        season = "LateWinter"
    else:
        raise ValueError(f"Date outside the source study windows: {day.isoformat()}")
    return f"{season}_{day.year}", season, day.year


def _optional_float(raw: str | None) -> float | None:
    value = (raw or "").strip()
    if not value or value.upper() in {"NA", "N/A", "UNKNOWN"}:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Expected a numeric building context value, got {value!r}") from exc


def _building_lookup(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, float | None]]:
    lookup: dict[str, dict[str, float | None]] = {}
    for row in rows:
        name = (row.get("Property Name") or "").strip()
        if not name:
            raise ValueError("Building inventory contains an empty Property Name")
        if name in lookup:
            raise ValueError(f"Duplicate building inventory name: {name}")
        lookup[name] = {
            "floors": _optional_float(row.get("Number floors")),
            "gross_area_m2": _optional_float(row.get("Gross Area sq m")),
        }
    return lookup


def build_facade_period_panel(
    fall_text: str,
    winter_text: str,
    buildings_text: str,
    *,
    strict_source: bool = False,
    source_hashes: Mapping[str, str] | None = None,
) -> tuple[list[dict], dict]:
    """Build one row per facade-by-author-defined survey period.

    Repeated evidence records on one facade-date count as multiple evidence
    records but only one survey visit. Missing visits are never filled with
    zeroes. Building inventory values are carried as context only.
    """
    fall_rows = _read_dict_rows(fall_text, SURVEY_FIELDS, "fall survey CSV")
    winter_rows = _read_dict_rows(winter_text, SURVEY_FIELDS, "winter survey CSV")
    building_rows = _read_dict_rows(buildings_text, BUILDING_FIELDS, "building inventory CSV")
    if strict_source:
        expected_rows = {
            "fall": SOURCE_FILES["fall"]["expected_rows"],
            "winter": SOURCE_FILES["winter"]["expected_rows"],
            "buildings": SOURCE_FILES["buildings"]["expected_rows"],
        }
        actual_rows = {"fall": len(fall_rows), "winter": len(winter_rows), "buildings": len(building_rows)}
        if actual_rows != expected_rows:
            raise ValueError(f"Pinned source row-count mismatch: {actual_rows}")
        if source_hashes is not None:
            for name, meta in SOURCE_FILES.items():
                if source_hashes.get(name) != meta["git_blob_sha"]:
                    raise ValueError(f"Unverified source hash for {name}")

    building_meta = _building_lookup(building_rows)
    visits: dict[tuple[str, str, date], dict] = {}
    facade_identity: dict[str, tuple[str, str]] = {}
    evidence_type_counts: Counter[str] = Counter()
    evidence_flag_counts: Counter[str] = Counter()
    missing_start_time_rows = 0
    inconsistent_evidence_rows = 0

    all_rows = [("fall", row) for row in fall_rows] + [("winter", row) for row in winter_rows]
    for source_name, row in all_rows:
        day = _parse_survey_date(row.get("SURVEY_DATE", ""))
        period_id, season, year = _period_for_date(day)
        building_id = (row.get("BUILDING_CODE") or "").strip()
        building_name = (row.get("BUILDING_NAME") or "").strip()
        facade_id = (row.get("FACADE") or "").strip()
        if not building_id or not building_name or not facade_id:
            raise ValueError(f"Missing building/facade identity in {source_name} source")
        identity = (building_id, building_name)
        previous = facade_identity.setdefault(facade_id, identity)
        if previous != identity:
            raise ValueError(f"Facade ID maps to multiple buildings: {facade_id}")

        found = (row.get("EVIDENCE_FOUND") or "").strip().upper()
        if found not in {"Y", "N"}:
            raise ValueError(f"Unexpected EVIDENCE_FOUND value: {found!r}")
        collision_type = (row.get("TYPE_OF_COLLISION") or "").strip().casefold() or "unknown"
        evidence_flag_counts[found] += 1
        evidence_type_counts[collision_type] += 1
        if (found == "Y") != (collision_type != "none"):
            inconsistent_evidence_rows += 1
        if not (row.get("SURVEY_START_TIME") or "").strip():
            missing_start_time_rows += 1

        key = (building_id, facade_id, day)
        if key not in visits:
            visits[key] = {
                "building_id": building_id,
                "building_name": building_name,
                "facade_id": facade_id,
                "date": day,
                "period_id": period_id,
                "season": season,
                "year": year,
                "raw_source_rows": 0,
                "collision_evidence_count": 0,
                "carcass_evidence_count": 0,
                "feather_pile_evidence_count": 0,
                "feather_smear_evidence_count": 0,
                "live_collision_evidence_count": 0,
            }
        visit = visits[key]
        visit["raw_source_rows"] += 1
        if found == "Y":
            visit["collision_evidence_count"] += 1
            if collision_type == "carcass":
                visit["carcass_evidence_count"] += 1
            elif collision_type == "feather pile":
                visit["feather_pile_evidence_count"] += 1
            elif collision_type == "feather smear":
                visit["feather_smear_evidence_count"] += 1
            elif collision_type == "collision_live":
                visit["live_collision_evidence_count"] += 1

    grouped: dict[tuple[str, str, str], dict] = {}
    for visit in visits.values():
        key = (visit["building_id"], visit["facade_id"], visit["period_id"])
        if key not in grouped:
            grouped[key] = {
                "facade_id": visit["facade_id"],
                "building_id": visit["building_id"],
                "building_name": visit["building_name"],
                "period_id": visit["period_id"],
                "season": visit["season"],
                "year": visit["year"],
                "dates": [],
                "survey_visits": 0,
                "collision_evidence_count": 0,
                "positive_visits": 0,
                "fatal_evidence_proxy_count": 0,
                "carcass_evidence_count": 0,
                "feather_pile_evidence_count": 0,
                "feather_smear_evidence_count": 0,
                "live_collision_evidence_count": 0,
                "raw_source_rows": 0,
            }
        panel_row = grouped[key]
        panel_row["dates"].append(visit["date"])
        panel_row["survey_visits"] += 1
        panel_row["collision_evidence_count"] += visit["collision_evidence_count"]
        panel_row["positive_visits"] += int(visit["collision_evidence_count"] > 0)
        panel_row["carcass_evidence_count"] += visit["carcass_evidence_count"]
        panel_row["feather_pile_evidence_count"] += visit["feather_pile_evidence_count"]
        panel_row["fatal_evidence_proxy_count"] += (
            visit["carcass_evidence_count"] + visit["feather_pile_evidence_count"]
        )
        panel_row["feather_smear_evidence_count"] += visit["feather_smear_evidence_count"]
        panel_row["live_collision_evidence_count"] += visit["live_collision_evidence_count"]
        panel_row["raw_source_rows"] += visit["raw_source_rows"]

    panel: list[dict] = []
    for row in grouped.values():
        dates = row.pop("dates")
        observed_visits = row["survey_visits"]
        metadata = building_meta.get(row["building_name"], {})
        expected_visits = EXPECTED_VISITS_PER_FACADE_PERIOD
        row.update({
            "period_start": min(dates).isoformat(),
            "period_end": max(dates).isoformat(),
            "expected_survey_visits": expected_visits,
            "missing_expected_visits": max(0, expected_visits - observed_visits),
            "effort_coverage": round(observed_visits / expected_visits, 6),
            "zero_evidence_visits": observed_visits - row["positive_visits"],
            "extra_source_rows_within_visits": row["raw_source_rows"] - observed_visits,
            "building_floors_context_2024": metadata.get("floors"),
            "building_gross_area_m2_context_2024": metadata.get("gross_area_m2"),
        })
        panel.append(row)

    panel.sort(key=lambda r: (r["period_start"], r["building_id"], r["facade_id"]))
    period_totals: dict[str, dict] = {}
    for row in panel:
        total = period_totals.setdefault(row["period_id"], {
            "survey_visits": 0,
            "collision_evidence_count": 0,
            "fatal_evidence_proxy_count": 0,
            "facades": 0,
            "missing_expected_visits": 0,
        })
        total["survey_visits"] += row["survey_visits"]
        total["collision_evidence_count"] += row["collision_evidence_count"]
        total["fatal_evidence_proxy_count"] += row["fatal_evidence_proxy_count"]
        total["facades"] += 1
        total["missing_expected_visits"] += row["missing_expected_visits"]

    audit = {
        "source_project": "vivizulian/BirdCollisionsUniVictoria",
        "source_branch": "sub2",
        "source_commit": SOURCE_COMMIT,
        "source_hashes_verified": bool(source_hashes),
        "source_git_blob_sha1": {name: meta["git_blob_sha"] for name, meta in SOURCE_FILES.items()},
        "source_row_counts": {
            "fall": len(fall_rows),
            "winter": len(winter_rows),
            "buildings": len(building_rows),
        },
        "grain": "one row per facade x author-defined seasonal survey period",
        "aggregation_rules": {
            "visit_key": "BUILDING_CODE + FACADE + parsed SURVEY_DATE",
            "survey_effort": "one unique facade-date visit; repeated evidence rows do not add visits",
            "collision_evidence": "count of source rows with EVIDENCE_FOUND == Y",
            "fatal_evidence_proxy": "carcass + feather pile records; not corrected mortality",
            "period_mapping": "months 9-10 Fall; month >=11 EarlyWinter; months 1-2 LateWinter; grouped by calendar year",
            "missing_visits": "not imputed as zero; survey_visits is the exposure offset",
        },
        "totals": {
            "raw_source_rows": len(all_rows),
            "unique_facade_day_visits": len(visits),
            "extra_source_rows_within_visits": len(all_rows) - len(visits),
            "facades": len(facade_identity),
            "buildings": len({identity[0] for identity in facade_identity.values()}),
            "periods": len(period_totals),
            "panel_rows": len(panel),
            "collision_evidence_count": sum(r["collision_evidence_count"] for r in panel),
            "fatal_evidence_proxy_count": sum(r["fatal_evidence_proxy_count"] for r in panel),
            "missing_survey_start_time_rows": missing_start_time_rows,
            "inconsistent_evidence_rows": inconsistent_evidence_rows,
        },
        "evidence_flag_counts": dict(sorted(evidence_flag_counts.items())),
        "evidence_type_counts": dict(sorted(evidence_type_counts.items())),
        "period_totals": period_totals,
        "limitations": [
            "No facade-level glass area, glazing appearance class or optical spectra in these files.",
            "No vegetation or canopy measurements in these files.",
            "2024 gross floor area and floor count are contextual only, not facade or glass area.",
            "Carcass and feather-pile records are evidence proxies, not detection-corrected mortality.",
            "This is a historical temperate-campus dataset, not a Guangdong/BNBU calibration sample.",
            "Survey evidence rates are not biological approach rates or absolute pane collision probabilities.",
        ],
    }

    if strict_source:
        totals = audit["totals"]
        for key, expected in EXPECTED_TOTALS.items():
            if totals[key] != expected:
                raise ValueError(f"Pinned data audit mismatch for {key}: {totals[key]} != {expected}")
        if inconsistent_evidence_rows != 0:
            raise ValueError("EVIDENCE_FOUND and TYPE_OF_COLLISION are inconsistent")
        if dict(evidence_flag_counts) != EXPECTED_EVIDENCE_FLAG_COUNTS:
            raise ValueError(f"Pinned evidence flags changed: {dict(evidence_flag_counts)}")
        if dict(evidence_type_counts) != EXPECTED_EVIDENCE_TYPE_COUNTS:
            raise ValueError(f"Pinned evidence types changed: {dict(evidence_type_counts)}")
        observed_period_totals = {
            key: (
                value["survey_visits"],
                value["collision_evidence_count"],
                value["fatal_evidence_proxy_count"],
            )
            for key, value in period_totals.items()
        }
        if observed_period_totals != EXPECTED_PERIOD_TOTALS:
            raise ValueError(f"Pinned period totals changed: {observed_period_totals}")
        if source_hashes is None:
            raise ValueError("strict_source requires verified source hashes")

    return panel, audit


def fit_observed_rate_gee(panel_rows: Sequence[Mapping[str, object]]) -> dict:
    """Fit an effort-offset Poisson GEE for observed evidence rates only.

    Building and period fixed effects are descriptive. Facade is the repeated
    cluster. No glass or vegetation coefficients are estimated because those
    features are absent from this source.
    """
    try:
        import numpy as np
        import pandas as pd
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError as exc:  # pragma: no cover - dependency error path
        raise RuntimeError("Install requirements.txt to fit the GEE baseline") from exc

    df = pd.DataFrame(panel_rows).copy()
    required = {
        "facade_id", "building_id", "period_id", "survey_visits",
        "collision_evidence_count", "fatal_evidence_proxy_count",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Panel is missing model fields: {sorted(missing)}")
    if df.empty:
        raise ValueError("Panel is empty")
    for column in ("survey_visits", "collision_evidence_count", "fatal_evidence_proxy_count"):
        df[column] = pd.to_numeric(df[column], errors="raise")
    if (df["survey_visits"] <= 0).any():
        raise ValueError("Every panel row must have positive observed survey effort")
    if (df["collision_evidence_count"] < 0).any() or (df["fatal_evidence_proxy_count"] < 0).any():
        raise ValueError("Evidence counts cannot be negative")
    if df["facade_id"].nunique() < 3 or df["building_id"].nunique() < 2 or df["period_id"].nunique() < 2:
        raise ValueError("GEE baseline requires at least 3 facades, 2 buildings and 2 periods")

    building_levels = sorted(df["building_id"].astype(str).unique())
    period_levels = sorted(df["period_id"].astype(str).unique())
    reference_building = "DTB" if "DTB" in building_levels else building_levels[0]
    reference_period = "Fall_2019" if "Fall_2019" in period_levels else period_levels[0]
    formula = (
        "collision_evidence_count ~ "
        f"C(building_id, Treatment(reference={reference_building!r})) + "
        f"C(period_id, Treatment(reference={reference_period!r}))"
    )
    model = smf.gee(
        formula=formula,
        groups="facade_id",
        data=df,
        offset=np.log(df["survey_visits"].astype(float)),
        family=sm.families.Poisson(),
        cov_struct=sm.cov_struct.Exchangeable(),
    )
    fitted = model.fit(maxiter=100)
    if not bool(getattr(fitted, "converged", True)):
        raise RuntimeError("Poisson GEE did not converge")

    confidence = fitted.conf_int()
    terms = []
    for term in fitted.params.index:
        estimate = float(fitted.params[term])
        lower = float(confidence.loc[term, 0])
        upper = float(confidence.loc[term, 1])
        terms.append({
            "term": str(term),
            "log_rate_ratio": estimate,
            "rate_ratio": exp(estimate),
            "ci95_lower_rate_ratio": exp(lower),
            "ci95_upper_rate_ratio": exp(upper),
            "p_value_robust": float(fitted.pvalues[term]),
        })

    period_rates = []
    for period, group in df.groupby("period_id", sort=True):
        effort = float(group["survey_visits"].sum())
        events = float(group["collision_evidence_count"].sum())
        fatal = float(group["fatal_evidence_proxy_count"].sum())
        period_rates.append({
            "period_id": str(period),
            "survey_visits": int(effort),
            "collision_evidence_count": int(events),
            "fatal_evidence_proxy_count": int(fatal),
            "observed_evidence_per_1000_facade_day_visits": 1000.0 * events / effort,
            "fatal_evidence_proxy_per_1000_facade_day_visits": 1000.0 * fatal / effort,
        })

    pearson = float(np.sum(np.square(np.asarray(fitted.resid_pearson, dtype=float))))
    df_resid = max(1, int(getattr(fitted, "df_resid", len(df) - len(terms))))
    dispersion = pearson / df_resid
    return {
        "model": "Poisson GEE with exchangeable within-facade working correlation",
        "target": "observed collision evidence count per surveyed facade-day",
        "formula": formula,
        "offset": "log(survey_visits)",
        "cluster": "facade_id",
        "covariance": "robust sandwich",
        "reference_building": reference_building,
        "reference_period": reference_period,
        "n_panel_rows": int(len(df)),
        "n_facades": int(df["facade_id"].nunique()),
        "n_buildings": int(df["building_id"].nunique()),
        "n_periods": int(df["period_id"].nunique()),
        "survey_visits": int(df["survey_visits"].sum()),
        "collision_evidence_count": int(df["collision_evidence_count"].sum()),
        "fatal_evidence_proxy_count": int(df["fatal_evidence_proxy_count"].sum()),
        "pearson_dispersion_ratio": dispersion,
        "converged": bool(getattr(fitted, "converged", True)),
        "coefficients": terms,
        "observed_period_rates": period_rates,
        "interpretation_limits": [
            "This models recorded evidence per surveyed facade-day, not true bird approach or absolute collision probability.",
            "Building and period effects are descriptive for these six buildings and six survey windows.",
            "No glass type, glass area, vegetation, canopy or illumination effects are estimable from this source.",
            "The carcass plus feather-pile endpoint is an evidence proxy and is not detection-corrected mortality.",
            "No out-of-site predictive accuracy is claimed; only six buildings are represented.",
        ],
    }


def write_panel_csv(panel_rows: Sequence[Mapping[str, object]], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PANEL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in panel_rows:
            writer.writerow({field: row.get(field) for field in PANEL_FIELDS})


def read_panel_csv(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(PANEL_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Panel CSV missing columns: {sorted(missing)}")
        rows = list(reader)
    for row in rows:
        for field in (
            "year", "survey_visits", "expected_survey_visits", "missing_expected_visits",
            "collision_evidence_count", "positive_visits", "zero_evidence_visits",
            "fatal_evidence_proxy_count", "carcass_evidence_count",
            "feather_pile_evidence_count", "feather_smear_evidence_count",
            "live_collision_evidence_count", "raw_source_rows",
            "extra_source_rows_within_visits",
        ):
            row[field] = int(row[field])
        for field in ("effort_coverage", "building_floors_context_2024", "building_gross_area_m2_context_2024"):
            row[field] = _optional_float(row[field])
    return rows


def write_json(data: Mapping[str, object], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
