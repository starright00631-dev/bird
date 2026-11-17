from __future__ import annotations

import csv
import io
import json

import pytest

from scripts.inspect_zulian_appendix import inspect_appendix, _read_csv


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def fixture_rows():
    return [
        {
            "Building": "A", "Facade": "A1", "FacArea": "100",
            "AreaGlass": "40", "VegPer": "35", "TreeCov": "20",
            "StorReflVeg": "2",
        },
        {
            "Building": "A", "Facade": "A2", "FacArea": "150",
            "AreaGlass": "60", "VegPer": "40", "TreeCov": "25",
            "StorReflVeg": "3",
        },
        {
            "Building": "B", "Facade": "B1", "FacArea": "80",
            "AreaGlass": "20", "VegPer": "10", "TreeCov": "0",
            "StorReflVeg": "0",
        },
    ]


def test_appendix_audit_finds_facade_covariates_and_unique_composite_keys():
    report = inspect_appendix(csv_bytes(fixture_rows()))
    assert report["row_count"] == 3
    assert report["key_audit"]["composite_key_unique"] is True
    assert report["key_audit"]["unique_composite_keys"] == 3
    assert report["feature_columns"]["facade_area"] == "FacArea"
    assert report["feature_columns"]["glass_area"] == "AreaGlass"
    assert report["feature_columns"]["porous_vegetation_percent"] == "VegPer"
    assert report["feature_columns"]["tree_cover_percent"] == "TreeCov"
    assert report["feature_columns"]["stories_reflecting_vegetation"] == "StorReflVeg"
    assert report["feature_summary"]["glass_area"]["glass_area_exceeds_facade_area"] == 0


def test_appendix_audit_flags_duplicate_facade_keys():
    rows = fixture_rows()
    rows.append(dict(rows[0]))
    report = inspect_appendix(csv_bytes(rows))
    assert report["key_audit"]["composite_key_unique"] is False
    assert report["key_audit"]["duplicate_composite_key_count"] == 1


def test_appendix_audit_flags_invalid_percentages_and_glass_area():
    rows = fixture_rows()
    rows[0]["VegPer"] = "120"
    rows[0]["AreaGlass"] = "120"
    report = inspect_appendix(csv_bytes(rows))
    assert report["feature_summary"]["porous_vegetation_percent"]["outside_0_100"] == 1
    assert report["feature_summary"]["glass_area"]["glass_area_exceeds_facade_area"] == 1


def test_appendix_reader_rejects_html_payload():
    with pytest.raises(ValueError, match="not a CSV"):
        _read_csv(b"<!DOCTYPE html><html><body>blocked</body></html>")


def test_appendix_reader_rejects_duplicate_normalized_headers():
    with pytest.raises(ValueError, match="duplicate/ambiguous"):
        _read_csv(b"Building,building\nA,A\n")
