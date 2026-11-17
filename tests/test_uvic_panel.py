from __future__ import annotations

import csv
import io

import pytest

from birdglass.uvic_panel import (
    _parse_survey_date,
    _period_for_date,
    build_facade_period_panel,
    fit_observed_rate_gee,
    git_blob_sha1,
    read_panel_csv,
    write_panel_csv,
)


def survey_row(day, building, facade, found="N", kind="none", start="09:00"):
    return {
        "SURVEY_DATE": day,
        "SEASON": "unused-source-label",
        "SKY_CONDITION_CODE": "1",
        "BUILDING_NAME": f"Building {building}",
        "BUILDING_CODE": building,
        "FACADE": facade,
        "SURVEY_START_TIME": start,
        "SURVEY_END_TIME": "09:10",
        "SURVEYOR": "XX",
        "EVIDENCE_FOUND": found,
        "TYPE_OF_COLLISION": kind,
        "COLLISION_TYPE_CATEGORY": "n",
        "GROUND_OR_WINDOW": "n",
        "NUMBER_OF_FEATHERS": "n",
        "SPECIES_ID": "NA",
        "CODE": "unused",
        "TAXONOMIC_GROUPING": "",
    }


def csv_text(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def buildings_text():
    rows = [
        {"Property Name": "Building A", "Number floors": "3", "Gross Area sq m": "1000"},
        {"Property Name": "Building B", "Number floors": "4", "Gross Area sq m": "2000"},
    ]
    return csv_text(rows)


def fixture_texts():
    fall = [
        survey_row("2019-09-16", "A", "A1", "Y", "carcass"),
        survey_row("2019-09-16", "A", "A1", "Y", "feather smear"),
        survey_row("2019-09-17", "A", "A1"),
        survey_row("2019-09-16", "B", "B1"),
        survey_row("2019-09-17", "B", "B1", "Y", "collision_live"),
    ]
    winter = [
        survey_row("11/22/21", "A", "A1", "Y", "feather pile"),
        survey_row("11/23/21", "A", "A1"),
        survey_row("11/22/21", "B", "B1"),
        survey_row("11/23/21", "B", "B1", "Y", "feather smear"),
    ]
    return csv_text(fall), csv_text(winter), buildings_text()


def test_date_parser_and_author_period_mapping():
    assert _parse_survey_date("2019-09-16").isoformat() == "2019-09-16"
    assert _parse_survey_date("1/21/20").isoformat() == "2020-01-21"
    assert _period_for_date(_parse_survey_date("11/22/21"))[0] == "EarlyWinter_2021"
    assert _period_for_date(_parse_survey_date("2/1/22"))[0] == "LateWinter_2022"
    with pytest.raises(ValueError, match="outside the source study windows"):
        _period_for_date(_parse_survey_date("2020-06-01"))


def test_git_blob_hash_is_not_plain_sha1():
    assert git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_panel_counts_unique_facade_days_and_preserves_multiple_evidence_rows():
    fall, winter, buildings = fixture_texts()
    panel, audit = build_facade_period_panel(fall, winter, buildings)
    assert len(panel) == 4
    assert audit["totals"]["raw_source_rows"] == 9
    assert audit["totals"]["unique_facade_day_visits"] == 8
    assert audit["totals"]["extra_source_rows_within_visits"] == 1
    assert audit["totals"]["collision_evidence_count"] == 5
    assert audit["totals"]["fatal_evidence_proxy_count"] == 2
    a_fall = next(r for r in panel if r["facade_id"] == "A1" and r["period_id"] == "Fall_2019")
    assert a_fall["survey_visits"] == 2
    assert a_fall["collision_evidence_count"] == 2
    assert a_fall["positive_visits"] == 1
    assert a_fall["zero_evidence_visits"] == 1
    assert a_fall["fatal_evidence_proxy_count"] == 1
    assert a_fall["extra_source_rows_within_visits"] == 1


def test_missing_visit_is_not_imputed_as_zero():
    fall, winter, buildings = fixture_texts()
    panel, _ = build_facade_period_panel(fall, winter, buildings)
    a_fall = next(r for r in panel if r["facade_id"] == "A1" and r["period_id"] == "Fall_2019")
    assert a_fall["survey_visits"] == 2
    assert a_fall["expected_survey_visits"] == 21
    assert a_fall["missing_expected_visits"] == 19
    assert a_fall["effort_coverage"] == pytest.approx(2 / 21)


def test_building_inventory_values_are_context_only_fields():
    fall, winter, buildings = fixture_texts()
    panel, _ = build_facade_period_panel(fall, winter, buildings)
    a_fall = next(r for r in panel if r["facade_id"] == "A1" and r["period_id"] == "Fall_2019")
    assert a_fall["building_floors_context_2024"] == 3.0
    assert a_fall["building_gross_area_m2_context_2024"] == 1000.0
    assert "glass_area_m2" not in a_fall
    assert "vegetation_cover_pct" not in a_fall


def test_invalid_evidence_flag_fails_closed():
    fall, winter, buildings = fixture_texts()
    fall = fall.replace(",Y,carcass,", ",maybe,carcass,", 1)
    with pytest.raises(ValueError, match="Unexpected EVIDENCE_FOUND"):
        build_facade_period_panel(fall, winter, buildings)


def test_facade_cannot_map_to_two_buildings():
    fall = [
        survey_row("2019-09-16", "A", "SHARED"),
        survey_row("2019-09-17", "B", "SHARED"),
    ]
    winter = [survey_row("11/22/21", "A", "A1")]
    with pytest.raises(ValueError, match="Facade ID maps to multiple buildings"):
        build_facade_period_panel(csv_text(fall), csv_text(winter), buildings_text())


def test_panel_csv_round_trip(tmp_path):
    fall, winter, buildings = fixture_texts()
    panel, _ = build_facade_period_panel(fall, winter, buildings)
    path = tmp_path / "panel.csv"
    write_panel_csv(panel, path)
    loaded = read_panel_csv(path)
    assert len(loaded) == len(panel)
    assert loaded[0]["survey_visits"] == panel[0]["survey_visits"]
    assert loaded[0]["effort_coverage"] == pytest.approx(panel[0]["effort_coverage"])


def test_gee_baseline_runs_and_does_not_claim_glass_or_vegetation_effects():
    rows = []
    for building in ("A", "B"):
        for facade_number in range(1, 4):
            facade = f"{building}{facade_number}"
            for period_index, period in enumerate(("Fall_2019", "LateWinter_2020", "Fall_2020")):
                rows.append({
                    "facade_id": facade,
                    "building_id": building,
                    "period_id": period,
                    "survey_visits": 20 if facade_number == 1 else 21,
                    "collision_evidence_count": (facade_number + period_index) % 4,
                    "fatal_evidence_proxy_count": (facade_number + period_index) % 2,
                })
    result = fit_observed_rate_gee(rows)
    assert result["converged"] is True
    assert result["n_panel_rows"] == 18
    assert result["n_facades"] == 6
    assert result["target"] == "observed collision evidence count per surveyed facade-day"
    assert any("No glass type" in item for item in result["interpretation_limits"])
    assert all("rate_ratio" in item for item in result["coefficients"])


def test_gee_refuses_rows_without_effort():
    rows = [
        {
            "facade_id": f"A{i}",
            "building_id": "A" if i < 2 else "B",
            "period_id": "P1" if i % 2 else "P2",
            "survey_visits": 0,
            "collision_evidence_count": 0,
            "fatal_evidence_proxy_count": 0,
        }
        for i in range(4)
    ]
    with pytest.raises(ValueError, match="positive observed survey effort"):
        fit_observed_rate_gee(rows)
