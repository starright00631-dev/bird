import csv
import hashlib
from pathlib import Path

import pytest

from scripts.audit_ubc_sources import (
    FILES,
    audit_carcass_persistence,
    audit_search_efficiency,
    audit_survey_table,
    download_file,
    read_csv,
)


def write_csv(path: Path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_facade_survey_preserves_explicit_zeroes(tmp_path):
    path = tmp_path / "appendix1.csv"
    write_csv(path, ["Building", "Facade", "Date", "Season", "Collision"], [
        {"Building": "A", "Facade": "A1", "Date": "2020-01-01", "Season": "winter", "Collision": "0"},
        {"Building": "A", "Facade": "A1", "Date": "2020-01-02", "Season": "winter", "Collision": "1"},
        {"Building": "B", "Facade": "B1", "Date": "2020-01-01", "Season": "winter", "Collision": "0"},
    ])
    result = audit_survey_table(path)
    assert result["rows"] == 3
    assert result["explicit_zero_rows"] == 2
    assert result["positive_rows"] == 1
    assert result["unique_counts"]["facade"] == 2
    assert result["unique_counts"]["building"] == 2


def test_search_efficiency_uses_sequential_risk_sets(tmp_path):
    path = tmp_path / "Search.Efficiency.csv"
    write_csv(path, ["ID", "s1", "s2", "s3"], [
        {"ID": "a", "s1": "1", "s2": "NA", "s3": "NA"},
        {"ID": "b", "s1": "0", "s2": "1", "s3": "NA"},
        {"ID": "c", "s1": "0", "s2": "0", "s3": "1"},
        {"ID": "d", "s1": "0", "s2": "0", "s3": "0"},
    ])
    result = audit_search_efficiency(path)
    hazards = result["conditional_detection_by_search"]
    assert hazards[0]["at_risk_trials_with_observed_result"] == 4
    assert hazards[0]["detections_on_this_search"] == 1
    assert hazards[1]["at_risk_trials_with_observed_result"] == 3
    assert hazards[1]["detections_on_this_search"] == 1
    assert hazards[2]["at_risk_trials_with_observed_result"] == 2
    assert hazards[2]["detections_on_this_search"] == 1


def test_persistence_requires_interval_censoring_fields(tmp_path):
    path = tmp_path / "Carcass.Persistence.csv"
    write_csv(path, ["ID", "LastPresent", "FirstAbsent"], [
        {"ID": "a", "LastPresent": "2.0", "FirstAbsent": "3.0"},
        {"ID": "b", "LastPresent": "4.0", "FirstAbsent": "NA"},
    ])
    result = audit_carcass_persistence(path)
    assert result["status"] == "interval_and_right_censoring_fields_detected"
    assert result["last_present_column"] == "LastPresent"
    assert result["first_absent_column"] == "FirstAbsent"
    assert result["interval_censored_trials"] == 1
    assert result["right_censored_trials"] == 1
    assert result["first_absent_na_trials"] == 1


def test_unknown_response_is_not_silently_zero(tmp_path):
    path = tmp_path / "appendix1.csv"
    write_csv(path, ["Building", "Facade", "Date", "Collision"], [
        {"Building": "A", "Facade": "A1", "Date": "2020-01-01", "Collision": "NA"},
        {"Building": "A", "Facade": "A1", "Date": "2020-01-02", "Collision": "0"},
    ])
    result = audit_survey_table(path)
    assert result["explicit_zero_rows"] == 1
    assert result["unknown_response_rows"] == 1


def test_csv_reader_rejects_duplicate_headers(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("A,A\n1,2\n", encoding="utf-8")
    try:
        read_csv(path)
    except ValueError as error:
        assert "Duplicate" in str(error)
    else:
        raise AssertionError("Duplicate headers should fail")


def test_public_search_efficiency_file_matches_dryad_md5():
    path = Path(__file__).parents[1] / "data" / "raw" / "ubc" / "Search.Efficiency.csv"
    assert path.exists()
    assert FILES["Search.Efficiency.csv"] == ("f9e7a8816ef52eb9d3523f0f14b40d6b", 1766)
    assert hashlib.md5(path.read_bytes()).hexdigest() == "f9e7a8816ef52eb9d3523f0f14b40d6b"
    result = audit_search_efficiency(path)
    assert result["rows"] == 29
    assert result["conditional_detection_by_search"][0]["detections_on_this_search"] == 16
    assert result["conditional_detection_by_search"][1]["at_risk_trials_with_observed_result"] == 13

def test_verified_search_efficiency_season_breakdown():
    path = Path(__file__).parents[1] / "data" / "raw" / "ubc" / "Search.Efficiency.csv"
    result = audit_search_efficiency(path)
    seasons = result["first_search_by_season"]
    assert seasons["fall"]["first_search_detections"] == 0
    assert seasons["fall"]["trials"] == 2
    assert seasons["spring"]["first_search_detections"] == 2
    assert seasons["summer"]["first_search_detections"] == 3
    assert seasons["winter"]["first_search_detections"] == 11



def test_download_file_verifies_checksum_before_writing(monkeypatch, tmp_path):
    payload = b"ID,s1" + bytes([10]) + b"carc1,1" + bytes([10])
    digest = hashlib.md5(payload).hexdigest()
    monkeypatch.setitem(FILES, "Search.Efficiency.csv", (digest, len(payload)))

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return payload

    monkeypatch.setattr(
        "scripts.audit_ubc_sources.urllib.request.urlopen",
        lambda request, timeout: FakeResponse(),
    )
    destination = tmp_path / "Search.Efficiency.csv"
    result = download_file("Search.Efficiency.csv", destination)
    assert destination.read_bytes() == payload
    assert result["md5"] == digest
    assert result["bytes"] == len(payload)


def test_download_file_rejects_checksum_mismatch_before_writing(monkeypatch, tmp_path):
    payload = b"ID,s1" + bytes([10]) + b"carc1,1" + bytes([10])
    monkeypatch.setitem(FILES, "Search.Efficiency.csv", ("0" * 32, len(payload)))

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return payload

    monkeypatch.setattr(
        "scripts.audit_ubc_sources.urllib.request.urlopen",
        lambda request, timeout: FakeResponse(),
    )
    destination = tmp_path / "Search.Efficiency.csv"
    with pytest.raises(ValueError, match="MD5 mismatch"):
        download_file("Search.Efficiency.csv", destination)
    assert not destination.exists()


def test_persistence_inf_is_right_censored(tmp_path):
    path = tmp_path / "Carcass.Persistence.csv"
    write_csv(path, ["ID", "LastPresent", "FirstAbsent"], [
        {"ID": "a", "LastPresent": "2.0", "FirstAbsent": "3.0"},
        {"ID": "b", "LastPresent": "4.0", "FirstAbsent": "Inf"},
        {"ID": "c", "LastPresent": "1.0", "FirstAbsent": "NA"},
    ])
    result = audit_carcass_persistence(path)
    assert result["interval_censored_trials"] == 1
    assert result["right_censored_trials"] == 2
    assert result["first_absent_inf_trials"] == 1
    assert result["first_absent_na_trials"] == 1
    assert result["invalid_or_incomplete_trials"] == 0


def test_persistence_rejects_absence_before_last_present(tmp_path):
    path = tmp_path / "Carcass.Persistence.csv"
    write_csv(path, ["ID", "LastPresent", "FirstAbsent"], [
        {"ID": "bad", "LastPresent": "4.0", "FirstAbsent": "3.0"},
        {"ID": "good", "LastPresent": "1.0", "FirstAbsent": "2.0"},
    ])
    result = audit_carcass_persistence(path)
    assert result["interval_censored_trials"] == 1
    assert result["invalid_or_incomplete_trials"] == 1
    assert result["invalid_ids"] == ["bad"]


def test_observed_collision_audit_separates_events_from_visits(tmp_path):
    from scripts.audit_ubc_sources import audit_observed_collision_counts

    path = tmp_path / "Observed.Collision.Counts.csv"
    write_csv(path, [
        "SURVEY_DATENO", "SURVEY_DATE", "BUILDING.X", "FACADE",
        "VEGE_CAT", "VEGE_PERC", "STOREYS", "COLLISIONMORTALITY_X", "METHOD",
    ], [
        {"SURVEY_DATENO": "1/1/2020", "SURVEY_DATE": "1/1/2020", "BUILDING.X": "A",
         "FACADE": "A1", "VEGE_CAT": "low", "VEGE_PERC": "0.2",
         "STOREYS": "3", "COLLISIONMORTALITY_X": "1", "METHOD": "1"},
        {"SURVEY_DATENO": "1/1/2020", "SURVEY_DATE": "1/1/2020", "BUILDING.X": "A",
         "FACADE": "A1", "VEGE_CAT": "low", "VEGE_PERC": "0.2",
         "STOREYS": "3", "COLLISIONMORTALITY_X": "1", "METHOD": "1"},
        {"SURVEY_DATENO": "1/1/2020", "SURVEY_DATE": "1/1/2020", "BUILDING.X": "A",
         "FACADE": "A2", "VEGE_CAT": "low", "VEGE_PERC": "0.2",
         "STOREYS": "2.5", "COLLISIONMORTALITY_X": "0", "METHOD": "1"},
    ])
    result = audit_observed_collision_counts(path)
    assert result["raw_rows"] == 3
    assert result["collision_event_count"] == 2
    assert result["positive_event_rows"] == 2
    assert result["positive_facade_date_visits"] == 1
    assert result["duplicate_facade_date_groups"] == 1
    assert result["duplicate_extra_positive_events"] == 1
    assert result["explicit_zero_rows"] == 1


def test_search_schedule_reports_seasonal_effort_windows(tmp_path):
    from scripts.audit_ubc_sources import audit_search_schedule

    path = tmp_path / "Search.Schedule.csv"
    write_csv(path, [
        "SearchDate", "Season", "Season.by.5", "A", "B"
    ], [
        {"SearchDate": "1/1/2020", "Season": "winter", "Season.by.5": "winter2020", "A": "1", "B": "1"},
        {"SearchDate": "1/2/2020", "Season": "winter", "Season.by.5": "winter2020", "A": "1", "B": "1"},
        {"SearchDate": "1/4/2020", "Season": "winter", "Season.by.5": "winter2020", "A": "1", "B": "1"},
    ])
    result = audit_search_schedule(path)
    assert result["unique_survey_dates"] == 3
    assert result["period_count"] == 1
    assert result["monitoring_days_total_inclusive"] == 4
    assert result["periods"]["winter2020"]["gap_days_distribution"] == {"1": 1, "2": 1}
    assert result["all_buildings_searched_on_every_scheduled_date"] is True


def test_point_count_audit_uses_checklist_not_species_row_grain(tmp_path):
    from scripts.audit_ubc_sources import audit_point_counts, UBC_STUDY_POINT_COUNT_LOCATIONS

    path = tmp_path / "UBC.point.counts.csv"
    study_location = sorted(UBC_STUDY_POINT_COUNT_LOCATIONS)[0]
    other_location = "University of British Columbia, Extra Annex"
    write_csv(path, [
        "Species", "Count", "Location", "Date", "Interval", "Start",
        "Duration_mins", "Distance_m", "Num_obs", "Complete_Checklist",
        "Num_spp_in_count",
    ], [
        {"Species": "Species A", "Count": "1", "Location": study_location,
         "Date": "25-Jan-17", "Interval": "1", "Start": "9:00 AM",
         "Duration_mins": "5", "Distance_m": "50", "Num_obs": "1",
         "Complete_Checklist": "TRUE", "Num_spp_in_count": "2"},
        {"Species": "Species B", "Count": "2", "Location": study_location,
         "Date": "25-Jan-17", "Interval": "1", "Start": "9:00 AM",
         "Duration_mins": "5", "Distance_m": "50", "Num_obs": "1",
         "Complete_Checklist": "TRUE", "Num_spp_in_count": "2"},
        {"Species": "Species C", "Count": "1", "Location": other_location,
         "Date": "25-Jan-17", "Interval": "1", "Start": "9:00 AM",
         "Duration_mins": "5", "Distance_m": "50", "Num_obs": "1",
         "Complete_Checklist": "TRUE", "Num_spp_in_count": "1"},
    ])
    result = audit_point_counts(path)
    assert result["species_rows"] == 3
    assert result["checklist_groups"] == 2
    assert result["study_building_checklists"] == 1
    assert result["nonstudy_checklists"] == 1
    assert result["checklist_group_size_mismatches"] == 0
    assert result["metadata_inconsistencies"] == 0


def test_observed_collision_audit_rejects_facade_id_reused_across_buildings(tmp_path):
    from scripts.audit_ubc_sources import audit_observed_collision_counts

    path = tmp_path / "Observed.Collision.Counts.csv"
    write_csv(path, [
        "SURVEY_DATE", "BUILDING.X", "FACADE", "VEGE_CAT", "VEGE_PERC",
        "STOREYS", "COLLISIONMORTALITY_X", "METHOD",
    ], [
        {"SURVEY_DATE": "1/1/2020", "BUILDING.X": "A", "FACADE": "shared",
         "VEGE_CAT": "low", "VEGE_PERC": "20", "STOREYS": "2",
         "COLLISIONMORTALITY_X": "0", "METHOD": "1"},
        {"SURVEY_DATE": "1/2/2020", "BUILDING.X": "B", "FACADE": "shared",
         "VEGE_CAT": "high", "VEGE_PERC": "80", "STOREYS": "3",
         "COLLISIONMORTALITY_X": "1", "METHOD": "1"},
    ])
    with pytest.raises(ValueError, match="maps to multiple buildings"):
        audit_observed_collision_counts(path)
