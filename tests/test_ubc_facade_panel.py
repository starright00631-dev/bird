import csv
import io
import json

import pytest

from scripts.build_ubc_facade_panel import PANEL_FIELDS, build_panel, write_panel


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
        "DIRECTION": "north",
        "ANGLE_FROM_LINEAR_DIR_MEAN": "90",
    }
    rows = []
    for facade, facade_area, glass_area in (("A1", "100", "40"), ("A2", "120", "60")):
        for day, method in (("2015-09-09", "1"), ("2015-09-10", "2")):
            row = dict(base)
            row["FACADE"] = facade
            row["SURVEY_DATE"] = day
            row["METHOD"] = method
            row["FACADE_AREA"] = facade_area
            row["AREA_GLASS"] = glass_area
            rows.append(row)
    rows[0]["COLLISIONMORTALITY_X"] = "1"
    rows[0]["COLLISIONS_X"] = "1"
    rows[1]["COLLISIONMORTALITY_X"] = "0"
    rows[1]["COLLISIONS_X"] = "2"
    return rows


def test_build_panel_maps_source_fields_and_derives_exposure():
    panel, audit = build_panel(csv_bytes(fixture_rows()), strict_source=False)

    assert len(panel) == 4
    assert set(panel[0]) == set(PANEL_FIELDS)
    assert audit["rows"] == 4
    assert audit["buildings"] == 1
    assert audit["facades"] == 2
    assert audit["unique_facade_date_keys"] == 4
    assert audit["mortality_events"] == 1
    assert audit["positive_mortality_visits"] == 1
    assert audit["other_collision_events"] == 3
    by_key = {(row["facade_label"], row["survey_date"]): row for row in panel}
    assert by_key[("A1", "2015-09-09")]["survey_hours"] == 24
    assert by_key[("A1", "2015-09-10")]["survey_hours"] == 48
    assert by_key[("A1", "2015-09-09")]["mortality_present"] == 1
    assert by_key[("A1", "2015-09-09")]["glass_fraction"] == pytest.approx(0.4)
    assert by_key[("A2", "2015-09-09")]["facade_porous_cover_percent"] == 35.0


def test_build_panel_rejects_duplicate_facade_date_key():
    rows = fixture_rows()
    rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match="Duplicate facade-date key"):
        build_panel(csv_bytes(rows), strict_source=False)


def test_build_panel_rejects_facade_static_feature_drift():
    rows = fixture_rows()
    rows[1]["AREA_GLASS"] = "41"
    with pytest.raises(ValueError, match="Facade-static predictors change"):
        build_panel(csv_bytes(rows), strict_source=False)


def test_build_panel_rejects_glass_area_above_facade_area():
    rows = fixture_rows()
    rows[0]["AREA_GLASS"] = "101"
    with pytest.raises(ValueError, match="Glass area outside"):
        build_panel(csv_bytes(rows), strict_source=False)


def test_build_panel_rejects_building_level_vegetation_drift():
    rows = fixture_rows()
    rows[-1]["VEGE_PERC"] = "0.45"
    with pytest.raises(ValueError, match="Building-level VEGE_PERC changes"):
        build_panel(csv_bytes(rows), strict_source=False)


def test_write_panel_writes_auditable_csv_and_json(tmp_path):
    panel, audit = build_panel(csv_bytes(fixture_rows()), strict_source=False)
    panel_path = tmp_path / "panel.csv"
    audit_path = tmp_path / "audit.json"
    write_panel(panel, panel_path, audit, audit_path)

    with panel_path.open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))
    written_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert len(written) == 4
    assert written_audit["rows"] == 4
    assert written_audit["source_sha256"] == audit["source_sha256"]


def test_build_panel_rejects_fractional_method_code():
    rows = fixture_rows()
    rows[0]["METHOD"] = "1.5"
    with pytest.raises(ValueError, match="Non-integer METHOD"):
        build_panel(csv_bytes(rows), strict_source=False)


def test_build_panel_preserves_fractional_stories_reflecting_canopy():
    rows = fixture_rows()
    # The published Appendix 1 contains fractional values on 26 of 57 facades.
    # This is a continuous reflected-canopy exposure measure; never round it.
    rows[0]["STORIES_REFLECT_CANOPY"] = "2.5"
    rows[1]["STORIES_REFLECT_CANOPY"] = "2.5"
    panel, _ = build_panel(csv_bytes(rows), strict_source=False)
    values = {
        row["stories_reflecting_canopy"]
        for row in panel if row["facade_id"] == "A::A1"
    }
    assert values == {2.5}
