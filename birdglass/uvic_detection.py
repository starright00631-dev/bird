"""Pinned UVic detection-trial and survey-schedule data audit."""
from __future__ import annotations
import csv, io
from collections import Counter
from datetime import datetime
from typing import Mapping
from urllib.request import Request, urlopen
from birdglass.uvic_panel import SOURCE_COMMIT, git_blob_sha1

DETECTION_SOURCE_FILES = {
    "searcher_efficiency": {
        "url": f"https://raw.githubusercontent.com/vivizulian/BirdCollisionsUniVictoria/{SOURCE_COMMIT}/Data/L0/searcher_efficiency_data/SearcherEfficiencyData.csv",
        "git_blob_sha": "6bbf00ab661847899f37efa6cbd6fdb0a922330b", "expected_rows": 79,
    },
    "search_schedule": {
        "url": f"https://raw.githubusercontent.com/vivizulian/BirdCollisionsUniVictoria/{SOURCE_COMMIT}/Data/L0/searcher_efficiency_data/SearcherScheduleData.csv",
        "git_blob_sha": "91e3bc33609e9320714d0ecbf7fd5fdf8fbfadac", "expected_rows": 126,
    },
    "carcass_persistence": {
        "url": f"https://raw.githubusercontent.com/vivizulian/BirdCollisionsUniVictoria/{SOURCE_COMMIT}/Data/L0/carcass_persistence_data/CarcassPersistenceData.csv",
        "git_blob_sha": "ff01730d5b877621814bc0dc295347ba9fef20bb", "expected_rows": 82,
    },
}
SEARCH_COLUMNS = ("s1", "s2", "s3", "s4", "s5")
BUILDING_COLUMNS = ("DTB", "EOW", "FIA", "MSB", "MWB", "UVC")
EXPECTED_RISK_SETS = {
    "s1": (79, 63, 16, 0), "s2": (13, 5, 8, 3), "s3": (8, 0, 8, 0),
    "s4": (8, 3, 5, 0), "s5": (4, 0, 4, 1),
}
EXPECTED_SCHEDULE_PERIODS = {
    "SepOct2019": 21, "JanFeb2020": 21, "SepOct2020": 21,
    "JanFeb2021": 21, "NovDec2021": 21, "JanFeb2022": 21,
}


def fetch_pinned_detection_sources(timeout: int = 45) -> tuple[dict[str, str], dict[str, str]]:
    texts, hashes = {}, {}
    for name, meta in DETECTION_SOURCE_FILES.items():
        req = Request(meta["url"], headers={"User-Agent": "BNBU-BirdGlass-Research/1.0"})
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
        actual = git_blob_sha1(raw)
        if actual != meta["git_blob_sha"]:
            raise ValueError(f"Pinned detection source changed for {name}: {actual}")
        texts[name] = raw.decode("utf-8-sig")
        hashes[name] = actual
    return texts, hashes


def _rows(text: str, required: set[str], label: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{label} missing fields: {sorted(missing)}")
    return [dict(row) for row in reader]


def _parse_date(value: str):
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((value or "").strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid search date: {value!r}")


def audit_detection_sources(search_efficiency_text: str, search_schedule_text: str,
                            carcass_persistence_text: str, *, strict_source: bool = False,
                            source_hashes: Mapping[str, str] | None = None) -> dict:
    search = _rows(search_efficiency_text,
        {"ID", "Season", "SeasonYear", "Building", "Building_Facade", *SEARCH_COLUMNS},
        "searcher-efficiency data")
    schedule = _rows(search_schedule_text,
        {"SearchDate", "SeasonYear", *BUILDING_COLUMNS}, "search schedule")
    persistence = _rows(carcass_persistence_text,
        {"ID", "Season", "SeasonYear", "BuildingFacade", "Building", "LastPresent", "FirstAbsent"},
        "carcass-persistence data")
    search_ids = [r["ID"].strip() for r in search]
    persistence_ids = [r["ID"].strip() for r in persistence]
    if any(not x for x in search_ids + persistence_ids):
        raise ValueError("Trial ID cannot be empty")

    risk_sets, invalid_codes, after_detection = [], 0, 0
    for j, occasion in enumerate(SEARCH_COLUMNS):
        risk = found = not_found = missing = 0
        for row in search:
            previous = [(row.get(c) or "NA").strip().upper() for c in SEARCH_COLUMNS[:j]]
            if not all(v == "0" for v in previous):
                continue
            value = (row.get(occasion) or "NA").strip().upper()
            if value in {"NA", ""}:
                missing += 1
            elif value in {"0", "1"}:
                risk += 1
                found += int(value == "1")
                not_found += int(value == "0")
        risk_sets.append({
            "occasion": occasion,
            "at_risk": risk,
            "at_risk_including_missing": risk + missing,
            "detected": found,
            "not_detected": not_found,
            "missing_outcome_while_at_risk": missing,
            "conditional_detection_fraction_observed": found / risk if risk else None,
        })
    for row in search:
        detected_before = False
        for occasion in SEARCH_COLUMNS:
            value = (row.get(occasion) or "NA").strip().upper()
            if detected_before and value not in {"NA", ""}:
                after_detection += 1
            if value == "1":
                detected_before = True
            elif value not in {"0", "1", "NA", ""}:
                invalid_codes += 1

    finite = right = day_zero = invalid_interval = missing_interval = 0
    for row in persistence:
        lp = (row.get("LastPresent") or "").strip()
        fa = (row.get("FirstAbsent") or "").strip().upper()
        if not lp or not fa:
            missing_interval += 1
            continue
        try:
            last = float(lp)
        except ValueError:
            missing_interval += 1
            continue
        if fa == "INF":
            right += 1
        else:
            try:
                first = float(fa)
            except ValueError:
                missing_interval += 1
                continue
            finite += 1
            day_zero += int(last == 0)
            invalid_interval += int(last > first)

    dates = [_parse_date(r["SearchDate"]) for r in schedule]
    period_counts = Counter(r["SeasonYear"].strip() for r in schedule)
    building_counts = {b: sum((r.get(b) or "").strip() == "1" for r in schedule) for b in BUILDING_COLUMNS}
    all_buildings = all(all((r.get(b) or "").strip() == "1" for b in BUILDING_COLUMNS) for r in schedule)
    search_set, persistence_set = set(search_ids), set(persistence_ids)
    audit = {
        "source_project": "vivizulian/BirdCollisionsUniVictoria",
        "source_commit": SOURCE_COMMIT,
        "source_hashes_verified": bool(source_hashes),
        "source_git_blob_sha1": {k: v["git_blob_sha"] for k, v in DETECTION_SOURCE_FILES.items()},
        "source_rows": {"searcher_efficiency_trials": len(search),
                        "search_schedule_dates": len(schedule),
                        "carcass_persistence_trials": len(persistence)},
        "searcher_efficiency": {
            "trial_ids_unique": len(search_set) == len(search_ids), "trial_count": len(search),
            "risk_sets": risk_sets, "invalid_observation_codes": invalid_codes,
            "observations_after_prior_detection": after_detection,
            "season_years": sorted({r["SeasonYear"].strip() for r in search}),
        },
        "carcass_persistence": {
            "trial_ids_unique": len(persistence_set) == len(persistence_ids), "trial_count": len(persistence),
            "finite_interval_observations": finite, "right_censored_observations": right,
            "last_present_at_day_zero": day_zero,
            "invalid_intervals_last_present_after_first_absent": invalid_interval,
            "missing_or_unparseable_intervals": missing_interval,
        },
        "schedule": {
            "unique_dates": len(set(dates)), "date_min": min(dates).isoformat() if dates else None,
            "date_max": max(dates).isoformat() if dates else None,
            "period_counts": dict(sorted(period_counts.items())),
            "building_survey_counts": building_counts,
            "all_six_buildings_surveyed_each_scheduled_date": all_buildings,
        },
        "trial_id_overlap_search_efficiency_and_persistence": len(search_set & persistence_set),
        "original_genest_specification": {
            "searcher_efficiency": "GenEst::pkm: p ~ Season, k ~ Season, obsCol s1-s5, allCombos=TRUE, bySeason=TRUE, allSeasons=TRUE",
            "carcass_persistence": "GenEst::cpm: l ~ Season, s ~ Season, LastPresent/FirstAbsent interval data, exponential/weibull/lognormal/loglogistic candidates, allCombos=TRUE",
            "mortality_estimator": "GenEst::estM: fixed survey schedule, facade unit, survey date, selected p and c models",
        },
        "refit_status": "source audit only; original GenEst model selection and estM mortality refit not yet run",
        "limitations": [
            "Conditional detection fractions are descriptive risk-set ratios, not fitted GenEst pkm estimates.",
            "Persistence intervals are not converted into survival curves or carcass persistence probabilities by this audit.",
            "Original GenEst model selection must be independently reproduced before mortality correction is used.",
        ],
    }
    if strict_source:
        expected_rows = {k: v["expected_rows"] for k, v in DETECTION_SOURCE_FILES.items()}
        actual_rows = {"searcher_efficiency": len(search), "search_schedule": len(schedule),
                       "carcass_persistence": len(persistence)}
        if actual_rows != expected_rows:
            raise ValueError(f"Pinned detection source row counts changed: {actual_rows}")
        if source_hashes is None:
            raise ValueError("strict_source requires verified detection source hashes")
        for name, meta in DETECTION_SOURCE_FILES.items():
            if source_hashes.get(name) != meta["git_blob_sha"]:
                raise ValueError(f"Unverified detection source hash for {name}")
        observed = {x["occasion"]: (x["at_risk"], x["detected"], x["not_detected"],
                                    x["missing_outcome_while_at_risk"]) for x in risk_sets}
        if observed != EXPECTED_RISK_SETS:
            raise ValueError(f"Pinned searcher-efficiency risk sets changed: {observed}")
        if dict(period_counts) != EXPECTED_SCHEDULE_PERIODS or not all_buildings or len(set(dates)) != 126:
            raise ValueError("Pinned survey schedule changed")
        if (finite, right, day_zero, invalid_interval, missing_interval) != (58, 24, 4, 0, 0):
            raise ValueError("Pinned carcass-persistence interval audit changed")
        if after_detection or invalid_codes or len(search_set) != 79 or len(persistence_set) != 82:
            raise ValueError("Invalid searcher-efficiency sequence or duplicate trial ID")
    return audit
