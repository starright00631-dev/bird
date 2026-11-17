#!/usr/bin/env python3
"""Checksum-pinned audit for UBC bird-window collision data.

De Groot et al. Dryad files and Zulian et al. Appendix 1 are distinct source
products. This script preserves explicit survey zeroes, repeated search
histories, and censored persistence intervals. It is not a collision model.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter
import hashlib
import json
import re
import statistics
import urllib.request
from datetime import datetime
from math import isfinite
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

    interval_ids = []
    right_censored_ids = []
    invalid_ids = []
    interval_widths = []
    first_absent_inf_ids = []
    first_absent_na_ids = []
    for row in rows:
        trial_id = row.get("ID") or row.get("Index") or row.get("cpID") or ""
        lo_raw, hi_raw = row.get(lower), row.get(upper)
        lo = number(lo_raw)
        hi = number(hi_raw)
        if lo is None or not isfinite(lo) or lo < 0:
            invalid_ids.append(trial_id)
            continue

        hi_token = (hi_raw or "").strip().casefold()
        hi_is_inf = hi_token in {"inf", "+inf", "infinity", "+infinity", "∞"}
        hi_is_na = missing(hi_raw)
        if hi_is_inf:
            first_absent_inf_ids.append(trial_id)
            right_censored_ids.append(trial_id)
            continue
        if hi_is_na:
            # GenEst accepts FirstAbsent=Inf or NA when the carcass remains
            # present at the final persistence-trial check.
            first_absent_na_ids.append(trial_id)
            right_censored_ids.append(trial_id)
            continue
        if hi is None or not isfinite(hi) or hi < lo:
            invalid_ids.append(trial_id)
            continue

        interval_ids.append(trial_id)
        interval_widths.append(hi - lo)

    return {
        "status": "interval_and_right_censoring_fields_detected",
        "rows": len(rows),
        "last_present_column": lower,
        "first_absent_column": upper,
        "interval_censored_trials": len(interval_ids),
        "right_censored_trials": len(right_censored_ids),
        "first_absent_inf_trials": len(first_absent_inf_ids),
        "first_absent_na_trials": len(first_absent_na_ids),
        "invalid_or_incomplete_trials": len(invalid_ids),
        "right_censored_ids": right_censored_ids,
        "invalid_ids": invalid_ids,
        "interval_width_days": {
            "n": len(interval_widths),
            "median": statistics.median(interval_widths) if interval_widths else None,
            "minimum": min(interval_widths) if interval_widths else None,
            "maximum": max(interval_widths) if interval_widths else None,
        },
        "interpretation": (
            "LastPresent and FirstAbsent bracket carcass removal. GenEst defines "
            "FirstAbsent=Inf or NA as persistence beyond the final trial check; "
            "these observations are right-censored, not finite removal times. "
            "Do not replace intervals with exact removal times."
        ),
    }


def _parse_ubc_date(value):
    raw = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported UBC date value: {raw!r}")


def audit_search_schedule(path):
    headers, rows = read_csv(path)
    required = {"SearchDate", "Season", "Season.by.5"}
    if required - set(headers):
        return {
            "status": "schema_mapping_required",
            "rows": len(rows),
            "columns": headers,
            "missing_required_columns": sorted(required - set(headers)),
        }
    building_columns = [
        h for h in headers if h not in {"SearchDate", "Season", "Season.by.5"}
    ]
    period_dates = {}
    dates = []
    search_counts = {name: 0 for name in building_columns}
    unscheduled_cells = 0
    missing_cells = 0
    for row in rows:
        day = _parse_ubc_date(row["SearchDate"])
        dates.append(day)
        period_dates.setdefault(row["Season.by.5"], []).append(day)
        for name in building_columns:
            value = (row.get(name) or "").strip()
            if value == "1":
                search_counts[name] += 1
            elif value == "0":
                unscheduled_cells += 1
            else:
                missing_cells += 1

    periods = {}
    monitoring_days_total = 0
    for period, values in sorted(period_dates.items()):
        ordered = sorted(set(values))
        gaps = [
            (ordered[i] - ordered[i - 1]).days
            for i in range(1, len(ordered))
        ]
        monitoring_days = (
            (ordered[-1] - ordered[0]).days + 1 if ordered else 0
        )
        monitoring_days_total += monitoring_days
        periods[period] = {
            "survey_dates": len(ordered),
            "start_date": ordered[0].isoformat() if ordered else None,
            "end_date": ordered[-1].isoformat() if ordered else None,
            "monitoring_days_inclusive": monitoring_days,
            "gap_days_distribution": dict(sorted(
                __import__("collections").Counter(gaps).items()
            )),
        }

    return {
        "status": "survey_schedule_schema_audited",
        "rows": len(rows),
        "unique_survey_dates": len(set(dates)),
        "building_columns": building_columns,
        "building_search_counts": search_counts,
        "all_buildings_searched_on_every_scheduled_date": (
            unscheduled_cells == 0 and missing_cells == 0
            and all(value == len(rows) for value in search_counts.values())
        ),
        "unscheduled_building_date_cells": unscheduled_cells,
        "missing_building_date_cells": missing_cells,
        "periods": periods,
        "period_count": len(periods),
        "monitoring_days_total_inclusive": monitoring_days_total,
        "interpretation": (
            "Each row is a scheduled search date and each building column records "
            "whether that building was searched. Long gaps between seasonal "
            "windows are not survey exposure days."
        ),
    }


def audit_observed_collision_counts(path, schedule_path=None):
    headers, rows = read_csv(path)
    required = {
        "SURVEY_DATE", "BUILDING.X", "FACADE", "VEGE_CAT", "VEGE_PERC",
        "STOREYS", "COLLISIONMORTALITY_X", "METHOD",
    }
    missing_columns = required - set(headers)
    if missing_columns:
        return {
            "status": "schema_mapping_required",
            "rows": len(rows),
            "columns": headers,
            "missing_required_columns": sorted(missing_columns),
        }

    grouped = {}
    facade_buildings = {}
    facade_dates = {}
    facade_storeys = {}
    vegetation_by_building = {}
    method_counts = {}
    date_field_mismatch_rows = 0
    positive_rows = 0
    explicit_zero_rows = 0
    collision_event_count = 0
    invalid_collision_values = 0

    schedule_rows = []
    schedule_columns = {}
    expected_method_by_date = {}
    schedule_by_date = {}
    if schedule_path is not None and Path(schedule_path).exists():
        schedule_headers, schedule_rows = read_csv(schedule_path)
        schedule_columns = {
            normalize(h): h for h in schedule_headers
            if h not in {"SearchDate", "Season", "Season.by.5"}
        }
        period_dates = {}
        for row in schedule_rows:
            day = _parse_ubc_date(row["SearchDate"])
            period_dates.setdefault(row["Season.by.5"], []).append(day)
            schedule_by_date[day] = row
        for period, values in period_dates.items():
            ordered = sorted(set(values))
            for index, day in enumerate(ordered):
                if index == 0:
                    expected_method_by_date[day] = 1  # clean-up / first survey of window
                else:
                    gap = (day - ordered[index - 1]).days
                    expected_method_by_date[day] = gap if gap in {1, 2} else 1

    method_schedule_mismatch_rows = 0
    method_schedule_checked_rows = 0
    unscheduled_observation_rows = 0
    for row in rows:
        day = _parse_ubc_date(row["SURVEY_DATE"])
        facade = (row.get("FACADE") or "").strip()
        building_code = (row.get("BUILDING.X") or "").strip()
        building_key = normalize(building_code)
        if not facade or not building_key:
            raise ValueError("Observed collision row has an empty facade/building ID")
        if row.get("SURVEY_DATENO") and row["SURVEY_DATENO"] != row["SURVEY_DATE"]:
            date_field_mismatch_rows += 1

        raw_count = number(row.get("COLLISIONMORTALITY_X"))
        if raw_count is None or not isfinite(raw_count) or raw_count < 0 or not raw_count.is_integer():
            invalid_collision_values += 1
            continue
        count = int(raw_count)
        collision_event_count += count
        positive_rows += int(count > 0)
        explicit_zero_rows += int(count == 0)
        key = (building_key, facade, day)
        group = grouped.setdefault(key, {
            "rows": 0, "positive_rows": 0, "collision_count": 0,
        })
        group["rows"] += 1
        group["positive_rows"] += int(count > 0)
        group["collision_count"] += count

        facade_buildings.setdefault(facade, building_key)
        facade_dates.setdefault(facade, set()).add(day)
        facade_storeys.setdefault(facade, set()).add(row.get("STOREYS", ""))
        vegetation = vegetation_by_building.setdefault(building_key, {
            "building_code": building_code, "vege_pct": set(), "vege_category": set()
        })
        vegetation["vege_pct"].add(row.get("VEGE_PERC", ""))
        vegetation["vege_category"].add(row.get("VEGE_CAT", ""))

        method = (row.get("METHOD") or "").strip()
        method_counts[method] = method_counts.get(method, 0) + 1
        if schedule_rows:
            schedule_row = schedule_by_date.get(day)
            schedule_column = schedule_columns.get(building_key)
            if schedule_row is None or schedule_column is None or schedule_row.get(schedule_column) != "1":
                unscheduled_observation_rows += 1
            expected_method = expected_method_by_date.get(day)
            if expected_method is not None:
                method_schedule_checked_rows += 1
                try:
                    if int(method) != expected_method:
                        method_schedule_mismatch_rows += 1
                except ValueError:
                    method_schedule_mismatch_rows += 1

    unique_dates = sorted({key[2] for key in grouped})
    facades = sorted(facade_buildings)
    duplicate_groups = {
        key: value for key, value in grouped.items() if value["rows"] > 1
    }
    positive_visits = sum(
        value["collision_count"] > 0 for value in grouped.values()
    )
    duplicate_extra_rows = sum(value["rows"] - 1 for value in duplicate_groups.values())
    duplicate_extra_positive_events = sum(
        max(0, value["positive_rows"] - 1)
        for value in duplicate_groups.values()
    )
    mixed_zero_positive_duplicate_groups = sum(
        value["positive_rows"] > 0 and value["positive_rows"] < value["rows"]
        for value in duplicate_groups.values()
    )
    zero_only_duplicate_groups = sum(
        value["positive_rows"] == 0 for value in duplicate_groups.values()
    )

    expected_keys = {
        (facade_buildings[facade], facade, day)
        for facade in facades for day in unique_dates
    }
    missing_keys = sorted(
        expected_keys - set(grouped),
        key=lambda item: (item[0], item[1], item[2]),
    )
    facade_visit_distribution = {}
    for count in sorted({len(days) for days in facade_dates.values()}):
        facade_visit_distribution[str(count)] = sum(
            len(days) == count for days in facade_dates.values()
        )
    noninteger_storeys = []
    inconsistent_storeys = []
    for facade, values in sorted(facade_storeys.items()):
        if len(values) != 1:
            inconsistent_storeys.append({"facade": facade, "values": sorted(values)})
            continue
        value = number(next(iter(values)))
        if value is not None and isfinite(value) and not value.is_integer():
            noninteger_storeys.append({
                "facade": facade,
                "value": next(iter(values)),
            })

    vegetation_summary = {
        building: {
            "building_code": value["building_code"],
            "vege_pct_values": sorted(value["vege_pct"]),
            "vege_category_values": sorted(value["vege_category"]),
            "constant_within_building": (
                len(value["vege_pct"]) == 1 and len(value["vege_category"]) == 1
            ),
        }
        for building, value in sorted(vegetation_by_building.items())
    }

    return {
        "status": "facade_date_event_grain_audited",
        "raw_rows": len(rows),
        "unique_buildings": len({facade_buildings[f] for f in facades}),
        "unique_facades": len(facades),
        "unique_survey_dates": len(unique_dates),
        "unique_facade_date_visits": len(grouped),
        "expected_full_facade_date_cross_product": len(facades) * len(unique_dates),
        "missing_facade_date_keys_vs_full_cross_product": len(missing_keys),
        "missing_facade_date_keys": [
            {"building": key[0], "facade": key[1], "date": key[2].isoformat()}
            for key in missing_keys
        ],
        "explicit_zero_rows": explicit_zero_rows,
        "positive_event_rows": positive_rows,
        "collision_event_count": collision_event_count,
        "positive_facade_date_visits": positive_visits,
        "duplicate_facade_date_groups": len(duplicate_groups),
        "duplicate_extra_rows": duplicate_extra_rows,
        "duplicate_extra_positive_events": duplicate_extra_positive_events,
        "mixed_zero_positive_duplicate_groups": mixed_zero_positive_duplicate_groups,
        "zero_only_duplicate_groups": zero_only_duplicate_groups,
        "facade_visit_count_distribution": facade_visit_distribution,
        "method_counts": dict(sorted(method_counts.items())),
        "method_schedule_checked_rows": method_schedule_checked_rows,
        "method_schedule_mismatch_rows": method_schedule_mismatch_rows,
        "unscheduled_observation_rows": unscheduled_observation_rows,
        "date_field_mismatch_rows": date_field_mismatch_rows,
        "invalid_collision_values": invalid_collision_values,
        "noninteger_storeys_facades": noninteger_storeys,
        "inconsistent_storeys_facades": inconsistent_storeys,
        "vegetation_by_building": vegetation_summary,
        "interpretation": (
            "One source row is an observed fatality record or an explicit zero "
            "survey record. Multiple positive rows on one facade-date represent "
            "multiple events, not duplicate survey effort. Aggregate to facade-date "
            "for visit-level presence/count targets, preserving both 152 events "
            "and 142 positive visits. Missing facade-date keys are not zeroes."
        ),
    }


UBC_STUDY_POINT_COUNT_LOCATIONS = {
    "University of British Columbia, Wesbrook building",
    "University of British Columbia, Irving K. Barber",
    "University of British Columbia, Osborne Centre Unit 1",
    "University of British Columbia, International House",
    "University of British Columbia, Asian Centre",
    "University of British Columbia, Place Vanier, Okanagan House",
    "University of British Columbia, Marine Drive Residence #6",
    "University of British Columbia, FP Innovations",
}


def audit_point_counts(path):
    headers, rows = read_csv(path)
    required = {
        "Species", "Count", "Location", "Date", "Interval", "Start",
        "Duration_mins", "Distance_m", "Num_obs", "Complete_Checklist",
        "Num_spp_in_count",
    }
    missing_columns = required - set(headers)
    if missing_columns:
        return {
            "status": "schema_mapping_required",
            "rows": len(rows),
            "columns": headers,
            "missing_required_columns": sorted(missing_columns),
        }

    groups = {}
    for row in rows:
        key = (
            (row.get("Location") or "").strip(),
            (row.get("Date") or "").strip(),
            (row.get("Interval") or "").strip(),
        )
        groups.setdefault(key, []).append(row)

    group_size_mismatches = []
    metadata_inconsistencies = []
    for key, group in groups.items():
        try:
            expected_species = int(float(group[0]["Num_spp_in_count"]))
        except (TypeError, ValueError):
            expected_species = -1
        if expected_species != len(group):
            group_size_mismatches.append({
                "location": key[0], "date": key[1], "interval": key[2],
                "rows": len(group), "Num_spp_in_count": group[0]["Num_spp_in_count"],
            })
        for field in (
            "Start", "Duration_mins", "Distance_m", "Num_obs",
            "Complete_Checklist", "Num_spp_in_count",
        ):
            if len({row.get(field, "") for row in group}) != 1:
                metadata_inconsistencies.append({
                    "location": key[0], "date": key[1], "interval": key[2],
                    "field": field,
                })

    study_groups = [
        key for key in groups if key[0] in UBC_STUDY_POINT_COUNT_LOCATIONS
    ]
    nonstudy_groups = [key for key in groups if key[0] not in UBC_STUDY_POINT_COUNT_LOCATIONS]
    locations = sorted({row["Location"] for row in rows})
    return {
        "status": "point_count_checklist_grain_audited",
        "species_rows": len(rows),
        "unique_species": len({row["Species"] for row in rows}),
        "unique_locations": len(locations),
        "locations": locations,
        "unique_dates": len({row["Date"] for row in rows}),
        "checklist_groups": len(groups),
        "study_building_locations": len({key[0] for key in study_groups}),
        "study_building_checklists": len(study_groups),
        "nonstudy_locations": len({key[0] for key in nonstudy_groups}),
        "nonstudy_checklists": len(nonstudy_groups),
        "checklist_group_size_mismatches": len(group_size_mismatches),
        "metadata_inconsistencies": len(metadata_inconsistencies),
        "group_size_mismatch_examples": group_size_mismatches[:10],
        "metadata_inconsistency_examples": metadata_inconsistencies[:10],
        "duration_mins_values": sorted({row["Duration_mins"] for row in rows}),
        "distance_m_values": sorted({row["Distance_m"] for row in rows}),
        "observer_count_values": sorted({row["Num_obs"] for row in rows}),
        "complete_checklist_values": sorted({row["Complete_Checklist"] for row in rows}),
        "interpretation": (
            "Each checklist is a Location x Date x Interval group with one row "
            "per species. The 72 checklists at the eight study-building locations "
            "are distinct from 14 ancillary checklists at two other locations. "
            "These winter point counts inform local site activity only; they are "
            "not facade approach denominators."
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



def audit_search_schedule(path):
    headers, rows = read_csv(path)
    required = {"SearchDate", "Season", "Season.by.5"}
    if required - set(headers):
        return {"status": "schema_mapping_required", "rows": len(rows),
                "columns": headers, "missing_required_columns": sorted(required - set(headers))}
    building_columns = [
        h for h in headers if h not in {"SearchDate", "Season", "Season.by.5"}
    ]
    period_dates = {}
    dates = []
    search_counts = {name: 0 for name in building_columns}
    unscheduled_cells = missing_cells = 0
    for row in rows:
        day = _parse_ubc_date(row["SearchDate"])
        dates.append(day)
        period_dates.setdefault(row["Season.by.5"], []).append(day)
        for name in building_columns:
            value = (row.get(name) or "").strip()
            if value == "1":
                search_counts[name] += 1
            elif value == "0":
                unscheduled_cells += 1
            else:
                missing_cells += 1
    periods = {}
    monitoring_days_total = 0
    for period, values in sorted(period_dates.items()):
        ordered = sorted(set(values))
        gaps = [(ordered[i] - ordered[i - 1]).days for i in range(1, len(ordered))]
        days = (ordered[-1] - ordered[0]).days + 1 if ordered else 0
        monitoring_days_total += days
        periods[period] = {
            "survey_dates": len(ordered),
            "start_date": ordered[0].isoformat() if ordered else None,
            "end_date": ordered[-1].isoformat() if ordered else None,
            "monitoring_days_inclusive": days,
            "gap_days_distribution": dict(sorted(Counter(gaps).items())),
        }
    return {
        "status": "survey_schedule_schema_audited",
        "rows": len(rows),
        "unique_survey_dates": len(set(dates)),
        "building_columns": building_columns,
        "building_search_counts": search_counts,
        "all_buildings_searched_on_every_scheduled_date": (
            unscheduled_cells == 0 and missing_cells == 0
            and all(value == len(rows) for value in search_counts.values())
        ),
        "unscheduled_building_date_cells": unscheduled_cells,
        "missing_building_date_cells": missing_cells,
        "periods": periods,
        "period_count": len(periods),
        "monitoring_days_total_inclusive": monitoring_days_total,
        "interpretation": (
            "Each row is a scheduled search date and each building column records "
            "whether that building was searched. Long gaps between seasonal "
            "windows are not survey exposure days."
        ),
    }


def audit_observed_collision_counts(path, schedule_path=None):
    headers, rows = read_csv(path)
    required = {
        "SURVEY_DATE", "BUILDING.X", "FACADE", "VEGE_CAT", "VEGE_PERC",
        "STOREYS", "COLLISIONMORTALITY_X", "METHOD",
    }
    missing_columns = required - set(headers)
    if missing_columns:
        return {
            "status": "schema_mapping_required", "rows": len(rows),
            "columns": headers, "missing_required_columns": sorted(missing_columns),
        }
    grouped = {}
    facade_buildings = {}
    facade_dates = {}
    facade_storeys = {}
    vegetation_by_building = {}
    method_counts = Counter()
    date_field_mismatch_rows = invalid_collision_values = 0
    positive_rows = explicit_zero_rows = collision_event_count = 0

    schedule_rows = []
    schedule_columns = {}
    expected_method_by_date = {}
    schedule_by_date = {}
    if schedule_path is not None and Path(schedule_path).exists():
        schedule_headers, schedule_rows = read_csv(schedule_path)
        schedule_columns = {
            normalize(h): h for h in schedule_headers
            if h not in {"SearchDate", "Season", "Season.by.5"}
        }
        period_dates = {}
        for row in schedule_rows:
            day = _parse_ubc_date(row["SearchDate"])
            period_dates.setdefault(row["Season.by.5"], []).append(day)
            schedule_by_date[day] = row
        for values in period_dates.values():
            ordered = sorted(set(values))
            for index, day in enumerate(ordered):
                if index == 0:
                    expected_method_by_date[day] = 1
                else:
                    gap = (day - ordered[index - 1]).days
                    expected_method_by_date[day] = gap if gap in {1, 2} else 1

    method_schedule_mismatch_rows = method_schedule_checked_rows = 0
    unscheduled_observation_rows = 0
    for row in rows:
        day = _parse_ubc_date(row["SURVEY_DATE"])
        facade = (row.get("FACADE") or "").strip()
        building_code = (row.get("BUILDING.X") or "").strip()
        building_key = normalize(building_code)
        if not facade or not building_key:
            raise ValueError("Observed collision row has an empty facade/building ID")
        if row.get("SURVEY_DATENO") and row["SURVEY_DATENO"] != row["SURVEY_DATE"]:
            date_field_mismatch_rows += 1
        raw_count = number(row.get("COLLISIONMORTALITY_X"))
        if raw_count is None or not isfinite(raw_count) or raw_count < 0 or not raw_count.is_integer():
            invalid_collision_values += 1
            continue
        count = int(raw_count)
        collision_event_count += count
        positive_rows += int(count > 0)
        explicit_zero_rows += int(count == 0)
        key = (building_key, facade, day)
        group = grouped.setdefault(key, {"rows": 0, "positive_rows": 0, "collision_count": 0})
        group["rows"] += 1
        group["positive_rows"] += int(count > 0)
        group["collision_count"] += count
        facade_buildings.setdefault(facade, building_key)
        facade_dates.setdefault(facade, set()).add(day)
        facade_storeys.setdefault(facade, set()).add(row.get("STOREYS", ""))
        vegetation = vegetation_by_building.setdefault(building_key, {
            "building_code": building_code, "vege_pct": set(), "vege_category": set()
        })
        vegetation["vege_pct"].add(row.get("VEGE_PERC", ""))
        vegetation["vege_category"].add(row.get("VEGE_CAT", ""))
        method = (row.get("METHOD") or "").strip()
        method_counts[method] += 1
        if schedule_rows:
            schedule_row = schedule_by_date.get(day)
            schedule_column = schedule_columns.get(building_key)
            if schedule_row is None or schedule_column is None or schedule_row.get(schedule_column) != "1":
                unscheduled_observation_rows += 1
            expected_method = expected_method_by_date.get(day)
            if expected_method is not None:
                method_schedule_checked_rows += 1
                try:
                    if int(method) != expected_method:
                        method_schedule_mismatch_rows += 1
                except ValueError:
                    method_schedule_mismatch_rows += 1

    unique_dates = sorted({key[2] for key in grouped})
    facades = sorted(facade_buildings)
    duplicate_groups = {key: value for key, value in grouped.items() if value["rows"] > 1}
    positive_visits = sum(value["collision_count"] > 0 for value in grouped.values())
    duplicate_extra_rows = sum(value["rows"] - 1 for value in duplicate_groups.values())
    duplicate_extra_positive_events = sum(
        max(0, value["positive_rows"] - 1) for value in duplicate_groups.values()
    )
    mixed_zero_positive_duplicate_groups = sum(
        value["positive_rows"] > 0 and value["positive_rows"] < value["rows"]
        for value in duplicate_groups.values()
    )
    zero_only_duplicate_groups = sum(value["positive_rows"] == 0 for value in duplicate_groups.values())
    expected_keys = {
        (facade_buildings[facade], facade, day)
        for facade in facades for day in unique_dates
    }
    missing_keys = sorted(expected_keys - set(grouped), key=lambda item: (item[0], item[1], item[2]))
    facade_visit_distribution = Counter(len(days) for days in facade_dates.values())
    noninteger_storeys = []
    inconsistent_storeys = []
    for facade, values in sorted(facade_storeys.items()):
        if len(values) != 1:
            inconsistent_storeys.append({"facade": facade, "values": sorted(values)})
            continue
        value = number(next(iter(values)))
        if value is not None and isfinite(value) and not value.is_integer():
            noninteger_storeys.append({"facade": facade, "value": next(iter(values))})
    vegetation_summary = {
        building: {
            "building_code": value["building_code"],
            "vege_pct_values": sorted(value["vege_pct"]),
            "vege_category_values": sorted(value["vege_category"]),
            "constant_within_building": len(value["vege_pct"]) == 1 and len(value["vege_category"]) == 1,
        }
        for building, value in sorted(vegetation_by_building.items())
    }
    return {
        "status": "facade_date_event_grain_audited",
        "raw_rows": len(rows),
        "unique_buildings": len({facade_buildings[f] for f in facades}),
        "unique_facades": len(facades),
        "unique_survey_dates": len(unique_dates),
        "unique_facade_date_visits": len(grouped),
        "expected_full_facade_date_cross_product": len(facades) * len(unique_dates),
        "missing_facade_date_keys_vs_full_cross_product": len(missing_keys),
        "missing_facade_date_keys": [
            {"building": key[0], "facade": key[1], "date": key[2].isoformat()}
            for key in missing_keys
        ],
        "explicit_zero_rows": explicit_zero_rows,
        "positive_event_rows": positive_rows,
        "collision_event_count": collision_event_count,
        "positive_facade_date_visits": positive_visits,
        "duplicate_facade_date_groups": len(duplicate_groups),
        "duplicate_extra_rows": duplicate_extra_rows,
        "duplicate_extra_positive_events": duplicate_extra_positive_events,
        "mixed_zero_positive_duplicate_groups": mixed_zero_positive_duplicate_groups,
        "zero_only_duplicate_groups": zero_only_duplicate_groups,
        "facade_visit_count_distribution": dict(sorted(facade_visit_distribution.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "method_schedule_checked_rows": method_schedule_checked_rows,
        "method_schedule_mismatch_rows": method_schedule_mismatch_rows,
        "unscheduled_observation_rows": unscheduled_observation_rows,
        "date_field_mismatch_rows": date_field_mismatch_rows,
        "invalid_collision_values": invalid_collision_values,
        "noninteger_storeys_facades": noninteger_storeys,
        "inconsistent_storeys_facades": inconsistent_storeys,
        "vegetation_by_building": vegetation_summary,
        "interpretation": (
            "One source row is an observed fatality record or an explicit zero survey record. "
            "Multiple positive rows on one facade-date represent multiple events, not duplicate "
            "survey effort. Aggregate to facade-date for visit-level presence/count targets, "
            "preserving 152 events and 142 positive visits. Missing facade-date keys are not zeroes."
        ),
    }


UBC_STUDY_POINT_COUNT_LOCATIONS = {
    "University of British Columbia, Wesbrook building",
    "University of British Columbia, Irving K. Barber",
    "University of British Columbia, Osborne Centre Unit 1",
    "University of British Columbia, International House",
    "University of British Columbia, Asian Centre",
    "University of British Columbia, Place Vanier, Okanagan House",
    "University of British Columbia, Marine Drive Residence #6",
    "University of British Columbia, FP Innovations",
}


def audit_point_counts(path):
    headers, rows = read_csv(path)
    required = {
        "Species", "Count", "Location", "Date", "Interval", "Start",
        "Duration_mins", "Distance_m", "Num_obs", "Complete_Checklist",
        "Num_spp_in_count",
    }
    missing_columns = required - set(headers)
    if missing_columns:
        return {
            "status": "schema_mapping_required", "rows": len(rows),
            "columns": headers, "missing_required_columns": sorted(missing_columns),
        }
    groups = {}
    for row in rows:
        key = (
            (row.get("Location") or "").strip(),
            (row.get("Date") or "").strip(),
            (row.get("Interval") or "").strip(),
        )
        groups.setdefault(key, []).append(row)
    group_size_mismatches = []
    metadata_inconsistencies = []
    for key, group in groups.items():
        try:
            expected_species = int(float(group[0]["Num_spp_in_count"]))
        except (TypeError, ValueError):
            expected_species = -1
        if expected_species != len(group):
            group_size_mismatches.append({
                "location": key[0], "date": key[1], "interval": key[2],
                "rows": len(group), "Num_spp_in_count": group[0]["Num_spp_in_count"],
            })
        for field in (
            "Start", "Duration_mins", "Distance_m", "Num_obs",
            "Complete_Checklist", "Num_spp_in_count",
        ):
            if len({row.get(field, "") for row in group}) != 1:
                metadata_inconsistencies.append({
                    "location": key[0], "date": key[1], "interval": key[2],
                    "field": field,
                })
    study_groups = [key for key in groups if key[0] in UBC_STUDY_POINT_COUNT_LOCATIONS]
    nonstudy_groups = [key for key in groups if key[0] not in UBC_STUDY_POINT_COUNT_LOCATIONS]
    locations = sorted({row["Location"] for row in rows})
    return {
        "status": "point_count_checklist_grain_audited",
        "species_rows": len(rows),
        "unique_species": len({row["Species"] for row in rows}),
        "unique_locations": len(locations),
        "locations": locations,
        "unique_dates": len({row["Date"] for row in rows}),
        "checklist_groups": len(groups),
        "study_building_locations": len({key[0] for key in study_groups}),
        "study_building_checklists": len(study_groups),
        "nonstudy_locations": len({key[0] for key in nonstudy_groups}),
        "nonstudy_checklists": len(nonstudy_groups),
        "checklist_group_size_mismatches": len(group_size_mismatches),
        "metadata_inconsistencies": len(metadata_inconsistencies),
        "group_size_mismatch_examples": group_size_mismatches[:10],
        "metadata_inconsistency_examples": metadata_inconsistencies[:10],
        "duration_mins_values": sorted({row["Duration_mins"] for row in rows}),
        "distance_m_values": sorted({row["Distance_m"] for row in rows}),
        "observer_count_values": sorted({row["Num_obs"] for row in rows}),
        "complete_checklist_values": sorted({row["Complete_Checklist"] for row in rows}),
        "interpretation": (
            "Each checklist is a Location x Date x Interval group with one row per species. "
            "The 72 checklists at the eight study-building locations are distinct from 14 "
            "ancillary checklists at two other locations. These winter point counts inform "
            "local site activity only; they are not facade approach denominators."
        ),
    }

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
    schedule_file = data_dir / "Search.Schedule.csv"
    observed_file = data_dir / "Observed.Collision.Counts.csv"
    point_file = data_dir / "UBC.point.counts.csv"
    if schedule_file.exists():
        result["search_schedule"] = audit_search_schedule(schedule_file)
    if observed_file.exists():
        result["observed_collision_counts"] = audit_observed_collision_counts(
            observed_file, schedule_file if schedule_file.exists() else None
        )
    if point_file.exists():
        result["point_counts"] = audit_point_counts(point_file)
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

