from __future__ import annotations

import csv
import io

import pytest

from scripts.inspect_zulian_appendix import inspect_appendix, _read_csv


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def fixture_rows():
    base = {
        "SURVEY_DATE": "2015-09-09",
        "SEASON": "fall",
        "BUILDING_X": "A",
        "METHOD": "1",
        "COLLISIONMORTALITY_X": "0",
        "COLLISIONS_X": "0",
        "FACADE_AREA": "100",
        "AREA_GLASS": "40",
        "PERC_VEG_AND_POROUS_SURFACE_FACADE": "35",
        "TREECOVER_FACADE_PERCENT": "20",
        "STORIES_REFLECT_CANOPY": "2",
        "VEGE_PERC": "0.35",
        "STOREYS": "3",
    }
    rows = []
    for facade in ("A1", "A2"):
        for day in ("2015-09-09", "2015-09-10"):
            row = dict(base)
            row["FACADE"] = facade
            row["SURVEY_DATE"] = day
            rows.append(row)
    rows[0]["COLLISIONMORTALITY_X"] = "1"
    rows[0]["COLLISIONS_X"] = "1"
    return rows


def test_appendix_audit_recognizes_repeated_facade_date_panel_and_features():
    report = inspect_appendix(csv_bytes(fixture_rows()))
    assert report["row_count"] == 4
    assert report["panel"]["facades"] == 2
    assert report["panel"]["survey_dates"] == 2
    assert report["panel"]["facade_date_rows"] == 4
    assert report["panel"]["duplicate_facade_date_keys"] == 0
    assert report["panel"]["complete_facade_date_grid"] is True
    assert report["outcomes"]["COLLISIONMORTALITY_X"]["sum"] == 1
    assert report["outcomes"]["COLLISIONMORTALITY_X"]["positive_rows"] == 1
    assert report["feature_columns"]["facade_area_m2"] == "FACADE_AREA"
    assert report["feature_columns"]["glass_area_m2"] == "AREA_GLASS"
    assert report["feature_columns"]["facade_porous_cover_percent"] == "PERC_VEG_AND_POROUS_SURFACE_FACADE"
    assert report["feature_columns"]["facade_tree_cover_percent"] == "TREECOVER_FACADE_PERCENT"
    assert report["feature_columns"]["stories_reflecting_canopy"] == "STORIES_REFLECT_CANOPY"


def test_appendix_audit_flags_duplicate_facade_date_key():
    rows = fixture_rows()
    rows.append(dict(rows[0]))
    report = inspect_appendix(csv_bytes(rows))
    assert report["panel"]["duplicate_facade_date_keys"] == 1
    assert report["panel"]["complete_facade_date_grid"] is False


def test_appendix_audit_flags_invalid_percentages_and_glass_area():
    rows = fixture_rows()
    rows[0]["PERC_VEG_AND_POROUS_SURFACE_FACADE"] = "120"
    rows[0]["AREA_GLASS"] = "120"
    report = inspect_appendix(csv_bytes(rows))
    assert report["feature_summary"]["facade_porous_cover_percent"]["outside_0_100"] == 1
    assert report["feature_summary"]["glass_area_m2"]["glass_area_exceeds_facade_area"] == 1


def test_appendix_reader_rejects_html_payload():
    with pytest.raises(ValueError, match="not a CSV"):
        _read_csv(b"<!DOCTYPE html><html><body>blocked</body></html>")


def test_appendix_reader_rejects_duplicate_headers():
    with pytest.raises(ValueError, match="duplicate headers"):
        _read_csv(b"Building,Building\nA,A\n")



def test_appendix_audit_flags_facade_feature_drift():
    rows = fixture_rows()
    rows[1]["AREA_GLASS"] = "41"
    report = inspect_appendix(csv_bytes(rows))
    summary = report["feature_summary"]["glass_area_m2"]
    assert summary["constant_within_facade"] is False
    assert summary["nonconstant_facade_count"] == 1


def test_de_groot_reconciliation_detects_distinct_source_grain_and_mismatches():
    appendix = fixture_rows()
    de_groot_rows = [
        {
            "SURVEY_DATE": "9/9/2015", "BUILDING_X": "A", "FACADE": "A1",
            "METHOD": "1", "COLLISIONMORTALITY_X": "0",
        },
        {
            "SURVEY_DATE": "9/9/2015", "BUILDING_X": "A", "FACADE": "A1",
            "METHOD": "1", "COLLISIONMORTALITY_X": "1",
        },
        {
            "SURVEY_DATE": "9/10/2015", "BUILDING_X": "A", "FACADE": "A1",
            "METHOD": "2", "COLLISIONMORTALITY_X": "0",
        },
        {
            "SURVEY_DATE": "9/9/2015", "BUILDING_X": "A", "FACADE": "A2",
            "METHOD": "1", "COLLISIONMORTALITY_X": "0",
        },
    ]
    report = inspect_appendix(
        csv_bytes(appendix),
        de_groot_raw=csv_bytes(de_groot_rows),
    )
    comparison = report["cross_source_reconciliation"]
    assert comparison["row_join_allowed"] is False
    assert comparison["facade_key_sets_equal"] is True
    assert comparison["common_facade_date_keys"] == 3
    assert comparison["appendix_only_facade_date_keys"] == 1
    assert comparison["de_groot_duplicate_facade_date_groups"] == 1
    assert comparison["method_mismatches_on_common_keys"] == 1


def test_strict_mode_rejects_unpinned_appendix_bytes():
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        inspect_appendix(csv_bytes(fixture_rows()), strict=True)
